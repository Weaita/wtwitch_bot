import asyncio
import json
import websockets
import requests
from bot import main
from tokens import get_app_access_token, get_broadcaster_id, is_channel_live
from config import CLIENT_ID, CHANNEL

async def eventsub_listener():
    app_token = await asyncio.to_thread(get_app_access_token)

    # Si ya está en vivo, arrancar bot inmediatamente
    if await asyncio.to_thread(is_channel_live, app_token):
        print("⚡ El canal ya está en directo. Iniciando bot de inmediato...")
        asyncio.create_task(main())

    broadcaster_id = await asyncio.to_thread(get_broadcaster_id, app_token)

    async with websockets.connect("wss://eventsub.wss.twitch.tv/ws") as ws:
        async for message in ws:
            data = json.loads(message)
            msg_type = data.get("metadata", {}).get("message_type")

            if msg_type == "session_welcome":
                session_id = data["payload"]["session"]["id"]
                sub_payload = {
                    "type": "stream.online",
                    "version": "1",
                    "condition": {"broadcaster_user_id": broadcaster_id},
                    "transport": {"method": "websocket", "session_id": session_id}
                }
                headers = {
                    "Client-ID": CLIENT_ID,
                    "Authorization": f"Bearer {app_token}",
                    "Content-Type": "application/json"
                }
                resp = requests.post(
                    "https://api.twitch.tv/helix/eventsub/subscriptions",
                    headers=headers, json=sub_payload
                )
                # Si el token de app caducó, conseguir uno nuevo y reintentar una vez
                if resp.status_code == 401:
                    app_token = await asyncio.to_thread(get_app_access_token)
                    headers["Authorization"] = f"Bearer {app_token}"
                    resp = requests.post(
                        "https://api.twitch.tv/helix/eventsub/subscriptions",
                        headers=headers, json=sub_payload
                    )
                print("✅ Suscripción EventSub creada:", resp.json())

            elif msg_type == "notification":
                event_type = data["payload"]["subscription"]["type"]
                if event_type == "stream.online":
                    print("🔴 El canal inició directo. Arrancando bot...")
                    asyncio.create_task(main())