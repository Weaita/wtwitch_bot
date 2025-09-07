import asyncio
import irc.client
from twitchAPI.twitch import Twitch
from config import CLIENT_ID, CLIENT_SECRET, CHANNEL, SCOPES
from commands import handle_command

async def main(twitch, access_token, refresh_token):
    await twitch.set_user_authentication(access_token, SCOPES, refresh_token=refresh_token)

    users = []
    async for user in twitch.get_users():
        users.append(user)
    username = users[0].login

    reactor = irc.client.Reactor()
    conn = reactor.server().connect("irc.chat.twitch.tv", 6667, username, password=f"oauth:{access_token}")

    def on_message(connection, event):
        msg = event.arguments[0]
        nick = event.source.nick
        # print(f"{nick}: {msg}")
        if msg.startswith('!') or msg.lower().startswith('@alphonse_bot7'):
            handle_command(connection, f"#{CHANNEL}", nick, msg)

    def send_hello(connection):
        connection.privmsg(f"#{CHANNEL}", "<3")

    def on_connect(connection, event):
        connection.join(f"#{CHANNEL}")
        print(f"[BOT.py]✅ Conectado a: #{CHANNEL}")
        reactor.scheduler.execute_after(5, lambda: send_hello(connection))

    conn.add_global_handler("welcome", on_connect)
    conn.add_global_handler("pubmsg", on_message)

    await asyncio.to_thread(reactor.process_forever)
