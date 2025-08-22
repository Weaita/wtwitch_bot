import asyncio
import irc.client
from twitchAPI.twitch import Twitch
from config import CLIENT_ID, CLIENT_SECRET, CHANNEL, SCOPES
from tokens import get_tokens, update_tokens, refresh_access_token, authenticate_and_store, ensure_fresh_user_tokens
from commands import handle_command

async def main():
    twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)

    access_token, refresh_token = get_tokens()

    if not access_token.strip() or not refresh_token.strip():
        access_token, refresh_token = await authenticate_and_store(twitch)

    # Asegurar tokens frescos antes de iniciar
    access_token, refresh_token, _ = ensure_fresh_user_tokens(min_seconds_left=600)

    try:
        # Refrescar una vez adicional al inicio para rotar refresh_token si es necesario
        access_token, refresh_token = refresh_access_token(CLIENT_ID, CLIENT_SECRET, refresh_token)
        update_tokens(access_token, refresh_token)
    except Exception as e:
        print("⚠️ Error al renovar token:", e)

    # Configurar autenticación de usuario para llamadas Helix iniciales
    await twitch.set_user_authentication(access_token, SCOPES, refresh_token=refresh_token)

    users = []
    async for user in twitch.get_users():
        users.append(user)
    username = users[0].login

    reactor = irc.client.Reactor()

    # Helpers para conectar y handlers
    def register_handlers(connection):
        def on_message(connection, event):
            msg = event.arguments[0]
            nick = event.source.nick
            if msg.startswith('!') or msg.lower().startswith('@alphonse_bot7'):
                handle_command(connection, f"#{CHANNEL}", nick, msg)

        def send_hello(connection):
            connection.privmsg(f"#{CHANNEL}", "<3")

        def on_connect(connection, event):
            connection.join(f"#{CHANNEL}")
            print(f"✅ Conectado a: #{CHANNEL}")
            reactor.scheduler.execute_after(5, lambda: send_hello(connection))

        connection.add_global_handler("welcome", on_connect)
        connection.add_global_handler("pubmsg", on_message)

    def connect_with_token(token_value: str):
        conn = reactor.server().connect("irc.chat.twitch.tv", 6667, username, password=f"oauth:{token_value}")
        register_handlers(conn)
        return conn

    conn = connect_with_token(access_token)

    # Mantenimiento periódico de tokens y reconexión si cambia
    def token_maintenance():
        nonlocal access_token, refresh_token, conn
        try:
            new_access, new_refresh, refreshed = ensure_fresh_user_tokens(min_seconds_left=600)
            if refreshed and new_access != access_token:
                print("♻️ Token refrescado. Reconectando a IRC con nuevo token…")
                access_token, refresh_token = new_access, new_refresh
                try:
                    conn.disconnect("refreshing token")
                except Exception:
                    pass
                conn = connect_with_token(access_token)
        except Exception as e:
            print("⚠️ Error en mantenimiento de tokens:", e)
        finally:
            # Reprogramar la siguiente verificación
            reactor.scheduler.execute_after(300, token_maintenance)

    # Programar la primera verificación en 5 minutos
    reactor.scheduler.execute_after(300, token_maintenance)

    reactor.process_forever()
