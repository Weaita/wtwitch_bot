# Se encarga de determinar cuándo iniciar el bot, ya sea si el canal ya está en vivo al iniciar el script o cuando
# recibe la notificación de que el canal ha iniciado directo mediante EventSub WebSocket.

import multiprocessing
import time
import asyncio
import json
import websockets
import requests
from twitchAPI.twitch import Twitch
from bot import main
from tokens import (
    get_tokens,
    get_broadcaster_id,
    is_channel_live,
    verify_tokens,
    saveTokensToJSONBIN,
    refresh_access_token,
    authenticate_and_store
)
from config import CLIENT_ID, CHANNEL, CLIENT_SECRET, WEBHOOK

bot_task = None  # referencia global a la tarea del bot
access_token = None
refresh_token = None
TOKEN_REFRESH_MARGIN = 300  # renovar 5 min antes de expirar

# Manejo de conexión WS
async def connect_eventsub(broadcaster_id, twitch, access_token, refresh_token,
                           url="wss://eventsub.wss.twitch.tv/ws", keepalive_seconds=30):
    base_ws_url = f"{url}?keepalive_timeout_seconds={keepalive_seconds}"
    ws_url = base_ws_url

    while True:
        try:
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as ws:
                # Después de una conexión exitosa, reseteamos la URL a la base.
                # Si recibimos un mensaje de reconexión, se actualizará de nuevo.
                # Esto evita reintentar con una URL de reconexión ya usada si la conexión se cae.
                ws_url = base_ws_url

                async for message in ws:
                    data = json.loads(message)
                    msg_type = data.get("metadata", {}).get("message_type")

                    if msg_type == "session_welcome":
                        session_id = data["payload"]["session"]["id"]
                        await asyncio.to_thread(subscribe_eventsub, session_id, broadcaster_id)


                    elif msg_type == "notification":
                        event_type = data["payload"]["subscription"]["type"]
                        if event_type == "stream.online":
                            asyncio.create_task(asyncio.to_thread(start_bot, twitch, access_token, refresh_token))
                        elif event_type == "stream.offline":
                            asyncio.create_task(asyncio.to_thread(stop_bot))

                    elif msg_type == "session_keepalive":
                        pass

                    elif msg_type == "session_reconnect":
                        new_url = data["payload"]["session"]["reconnect_url"]
                        await asyncio.to_thread(requests.post, WEBHOOK,
                                                json={"content": "[WS]♻️ Reconnect requerido. Intentando reconectar a la nueva URL."})
                        ws_url = new_url
                        break

            # tras reconnect
            await asyncio.sleep(0.5)

        except websockets.exceptions.ConnectionClosedError as e:
            # Error 4007: Reseteamos a la URL base para asegurar que el próximo intento sea una sesión nueva y válida
            await asyncio.to_thread(requests.post, WEBHOOK, json={"content": "⚠️ WS cerrado"})
            print(f"WS cerrado ({getattr(e, 'code', None)}): {e}. Reintentando...")
            ws_url = base_ws_url
            await asyncio.sleep(2)
            continue
        except Exception as e:
            print("Error WS, reintentando:", e)
            ws_url = base_ws_url
            await asyncio.sleep(5)
            continue


# Listener principal
async def eventsub_listener():
    global access_token, refresh_token
    twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)
    access_token, refresh_token = await asyncio.to_thread(get_tokens)

    if not verify_tokens(access_token):
        print("ERROR: Access token no válido, actualizando...")
        access_token, refresh_token, expires_in = await asyncio.to_thread(refresh_access_token, CLIENT_ID, CLIENT_SECRET, refresh_token, False)
        if not access_token and not refresh_token:
            print("No se encontraron tokens válidos. Abriendo navegador para autenticar...")
            await asyncio.to_thread(requests.post, WEBHOOK, json={"content": "⚠️ Abriendo navegador para autenticar... ⚠️"})
            access_token, refresh_token = await authenticate_and_store(twitch)

    broadcaster_id = await asyncio.to_thread(get_broadcaster_id, access_token)

    if await asyncio.to_thread(is_channel_live, access_token):
        print("🟢 El canal ya está en directo. Iniciando bot de inmediato...")
        start_bot(twitch, access_token, refresh_token)

    asyncio.create_task(refresh_tokens_periodically())
    
    await connect_eventsub(broadcaster_id, twitch, access_token, refresh_token)


# ------------------------
# Manejo de Tokens
# ------------------------
async def refresh_tokens_periodically():
    global access_token, refresh_token

    # Inicializamos la duración restante del token
    token_expires_at = time.time() + 3600  # valor inicial arbitrario, se actualizará al refrescar

    while True:
        now = time.time()
        sleep_time = max(token_expires_at - now - TOKEN_REFRESH_MARGIN, 60)
        await asyncio.sleep(sleep_time)

        try:
            # refresca el token y obtiene expires_in
            new_access, new_refresh, expires_in = await asyncio.to_thread(refresh_access_token, CLIENT_ID, CLIENT_SECRET, refresh_token)

            if new_access and new_refresh:
                access_token = new_access
                refresh_token = new_refresh
                # saveTokensToJSONBIN(access_token, refresh_token)
                token_expires_at = time.time() + expires_in
                print(f"✅ Tokens renovados. Próxima renovación en {int(expires_in - TOKEN_REFRESH_MARGIN)}s")
            else:
                print("❌ No se pudo renovar el token. Se requiere autenticación manual")
                await asyncio.to_thread(requests.post, WEBHOOK, json={"content": "⚠️ No se pudo renovar el token. Se requiere autenticación manual ⚠️"})
        except Exception as e:
            print("❌ Error al renovar tokens:", e)
            await asyncio.to_thread(requests.post, WEBHOOK, json={"content": "❌ Error al renovar tokens ❌"})
            # reintento en 1 minuto si falla
            await asyncio.sleep(60)

# ------------------------
# Suscripciones
# ------------------------
def subscribe_eventsub(session_id, broadcaster_id):
    global access_token
    for ev_type in ["stream.online", "stream.offline"]:
        sub_payload = {
            "type": ev_type,
            "version": "1",
            "condition": {"broadcaster_user_id": broadcaster_id},
            "transport": {"method": "websocket", "session_id": session_id}
        }
        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        resp = requests.post(
            "https://api.twitch.tv/helix/eventsub/subscriptions",
            headers=headers, json=sub_payload
        )
        print(f"✅ Suscripción {ev_type} creada:", resp.json())

# ------------------------
# Bot lifecycle
# ------------------------
bot_process = None

def run_bot(access_token, refresh_token):
    """Función que se ejecuta dentro del proceso hijo"""
    import asyncio
    from twitchAPI.twitch import Twitch
    from config import CLIENT_ID, CLIENT_SECRET
    from bot import main

    print("[run_bot] Proceso hijo iniciado")  # Debug print
    twitch = Twitch(CLIENT_ID, CLIENT_SECRET)
    if asyncio.iscoroutinefunction(main):
        asyncio.run(main(twitch, access_token, refresh_token))
    else:
        main(twitch, access_token, refresh_token)

def start_bot(twitch, access_token, refresh_token):
    global bot_process
    if bot_process and bot_process.is_alive():
        print("⚠️ Bot ya corriendo")
        return

    bot_process = multiprocessing.Process(
        target=run_bot, args=(access_token, refresh_token), daemon=True
    )
    bot_process.start()
    print(f"✅ Bot arrancado en proceso (PID={bot_process.pid})")

    # Espera hasta 10 segundos, verificando cada segundo si el proceso está vivo
    for _ in range(10):
        time.sleep(1)
        if bot_process.is_alive():
            break

    if not bot_process.is_alive():
        print("❌ El bot no inició correctamente. Reintentando...")
        bot_process = multiprocessing.Process(
            target=run_bot, args=(access_token, refresh_token), daemon=True
        )
        bot_process.start()
        print(f"🔄 Reintento: Bot arrancado en proceso (PID={bot_process.pid})")

def stop_bot():
    global bot_process
    if bot_process and bot_process.is_alive():
        print("🛑 Deteniendo bot...")
        bot_process.terminate()
        bot_process.join()
        bot_process = None
        print("✅ Bot detenido")
    else:
        print("⚠️ No había bot corriendo para detener.")

