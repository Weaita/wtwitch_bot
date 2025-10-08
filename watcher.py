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
STREAM_CHECK_INTERVAL = 300  # 5 minutos en segundos

# Manejo de conexión WS
async def connect_eventsub(broadcaster_id, twitch, access_token, refresh_token,
                           url="wss://eventsub.wss.twitch.tv/ws", keepalive_seconds=30):
    base_ws_url = f"{url}?keepalive_timeout_seconds={keepalive_seconds}"
    ws_url = base_ws_url

    while True:
        try:
            print(f"[WebSocket] Attempting to connect to {ws_url}")
            async with websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as ws:
                print("[WebSocket] Connection established")
                ws_url = base_ws_url

                async for message in ws:
                    data = json.loads(message)
                    msg_type = data.get("metadata", {}).get("message_type")
                    
                    # Detailed logging for each message type
                    print(f"[WebSocket] Message Type: {msg_type}")
                    
                    if msg_type == "session_welcome":
                        session_id = data["payload"]["session"]["id"]
                        print(f"[WebSocket] Welcome received. Session ID: {session_id}")
                        await asyncio.to_thread(subscribe_eventsub, session_id, broadcaster_id)

                    elif msg_type == "notification":
                        event_type = data["payload"]["subscription"]["type"]
                        print(f"[WebSocket] Notification received. Event type: {event_type}")
                        print(f"[WebSocket] Full payload: {json.dumps(data['payload'], indent=2)}")
                        
                        if event_type == "stream.online":
                            print("[WebSocket] Stream online event detected. Starting bot...")
                            await asyncio.to_thread(requests.post, WEBHOOK, 
                                json={"content": "🟢 Stream online detected! Starting bot..."})
                            await asyncio.to_thread(start_bot, twitch, access_token, refresh_token)
                            
                        elif event_type == "stream.offline":
                            print("[WebSocket] Stream offline event detected. Stopping bot...")
                            await asyncio.to_thread(requests.post, WEBHOOK,
                                json={"content": "🔴 Stream offline detected! Stopping bot..."})
                            await asyncio.to_thread(stop_bot)

                    elif msg_type == "session_keepalive":
                        print("[WebSocket] Keepalive received")

                    elif msg_type == "session_reconnect":
                        new_url = data["payload"]["session"]["reconnect_url"]
                        print(f"[WebSocket] Reconnect required. New URL: {new_url}")
                        await asyncio.to_thread(requests.post, WEBHOOK,
                            json={"content": "[WS]♻️ Reconnect requerido. Intentando reconectar..."})
                        ws_url = new_url
                        break

            await asyncio.sleep(0.5)

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"[WebSocket] Connection closed ({getattr(e, 'code', None)}): {e}")
            await asyncio.to_thread(requests.post, WEBHOOK, 
                json={"content": f"⚠️ WS cerrado (code: {getattr(e, 'code', None)})"})
            ws_url = base_ws_url
            await asyncio.sleep(2)
            continue
        except Exception as e:
            print(f"[WebSocket] Error: {str(e)}")
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
    # Añadir esta línea para iniciar la verificación periódica
    asyncio.create_task(check_stream_periodically(twitch, access_token, refresh_token))
    
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
    try:
        if bot_process and bot_process.is_alive():
            print("⚠️ Bot ya corriendo (PID: {bot_process.pid})")
            return

        print("[Bot] Iniciando nuevo proceso del bot...")
        bot_process = multiprocessing.Process(
            target=run_bot, args=(access_token, refresh_token), daemon=True
        )
        bot_process.start()
        print(f"✅ Bot arrancado en proceso (PID={bot_process.pid})")

        # Espera hasta 10 segundos, verificando cada segundo si el proceso está vivo
        for i in range(10):
            time.sleep(1)
            if bot_process.is_alive():
                print(f"[Bot] Proceso confirmado vivo después de {i+1}s")
                requests.post(WEBHOOK, json={"content": f"✅ Bot iniciado exitosamente (PID: {bot_process.pid})"})
                return
            print(f"[Bot] Esperando confirmación de proceso ({i+1}/10s)...")

        print("❌ El bot no inició correctamente. Reintentando...")
        requests.post(WEBHOOK, json={"content": "⚠️ Reintentando inicio del bot..."})
        
        bot_process = multiprocessing.Process(
            target=run_bot, args=(access_token, refresh_token), daemon=True
        )
        bot_process.start()
        print(f"🔄 Reintento: Bot arrancado en proceso (PID={bot_process.pid})")
        
    except Exception as e:
        error_msg = f"❌ Error al iniciar el bot: {str(e)}"
        print(error_msg)
        requests.post(WEBHOOK, json={"content": error_msg})

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

async def check_stream_periodically(twitch, access_token, refresh_token):
    while True:
        try:
            is_live = await asyncio.to_thread(is_channel_live, access_token)
            
            status = "🟢 ONLINE" if is_live else "🔴 OFFLINE"
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] Verificación periódica: {CHANNEL} está {status}")
            
            if is_live and (not bot_process or not bot_process.is_alive()):
                print("🔍 Detección periódica: Stream activo pero bot inactivo")
                await asyncio.to_thread(requests.post, WEBHOOK, 
                    json={"content": "🔍 Stream detectado activo en verificación periódica. Iniciando bot..."})
                await asyncio.to_thread(start_bot, twitch, access_token, refresh_token)
            
            await asyncio.sleep(STREAM_CHECK_INTERVAL)
            
        except Exception as e:
            print(f"❌ Error en verificación periódica: {str(e)}")
            await asyncio.sleep(60)  # Espera 1 minuto antes de reintentar si hay error

