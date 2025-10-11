from config import EMOCIONES, DATOS_CANAL, SYSTEM_PROMPT, PERSONALIDAD_ACTUAL, CHANNEL, USER_ROLES
from gemini import query_gemini
import random
import threading

def cmd_ping(conn, chan, user, prompt):
    conn.privmsg(chan, f'{user}, pong!')
    print(f'@{user} pong!')

def cmd_hervidor(conn, chan, user, prompt, delay_seconds: int = 300):
    conn.privmsg(chan, 'Vale, le aviso en 5 minutos ☕︎☕︎☕︎')
    def _send_remember():
        conn.privmsg(chan, f'@{CHANNEL} el hervidor!!😲☕︎☕︎☕︎')

    timer = threading.Timer(delay_seconds, _send_remember)
    timer.start()

def cmd_personalidad(conn, chan, user, prompt):
    if not prompt.strip():
        conn.privmsg(chan, f"{user}, debes indicar una personalidad. Ej: !wperso triste")
        return
    tipo = prompt.strip().lower()
    if tipo in EMOCIONES:
        PERSONALIDAD_ACTUAL[CHANNEL] = tipo
        print(f"🔄 Personalidad de {CHANNEL}: {tipo}")

CUSTOM_COMMANDS = {}

def cmd_crearcomando(conn, chan, user, prompt):
    args = prompt.strip().split(" ", 1)
    # Si no se da nombre, error
    if not args[0]:
        conn.privmsg(chan, f"@{user} ❌ Ej: !wcomando saludo Hola")
        return

    cmd_name = args[0].lower()
    if not cmd_name.startswith("!"):
        cmd_name = f"!{cmd_name}"

    # Si solo se da el nombre, se borra el comando
    if len(args) == 1 or not args[1].strip():
        if cmd_name in CUSTOM_COMMANDS:
            del CUSTOM_COMMANDS[cmd_name]
            conn.privmsg(chan, f"{user}, comando {cmd_name} eliminado.")
        else:
            conn.privmsg(chan, f"{user}, el comando {cmd_name} no existe.")
        return

    # Crear o sobrescribir comando
    CUSTOM_COMMANDS[cmd_name] = args[1].strip()
    conn.privmsg(chan, f"{user}, comando {cmd_name} creado/actualizado.")

def cmd_presentacion(conn, chan, user, prompt):
    conn.privmsg(chan, 'Hoola, soy Alphonse BOT, estoy a su servicio <3')

SALUDOS_PERSONALIZADOS = {
    "mafyta": "¡Hola mi querida Mafyta! <3. ¿Cómo has estado?",
    "sadistic_boar": "Sadiii 🥰, qué gusto tenerte en el chat 💖. ¿Cómo has estado?",
    "kevincamacena": "Keev 🥰, qué gusto tenerte en el chat fiera, máquina, mastodonte 💖",
}

# Set para guardar quiénes ya fueron saludados
USUARIOS_SALUDADOS = set()

def saludar_usuario(conn, chan, user):
    user_lower = user.lower()
    if user_lower not in USUARIOS_SALUDADOS:
        if user_lower in SALUDOS_PERSONALIZADOS:
            saludo = SALUDOS_PERSONALIZADOS[user_lower]
            conn.privmsg(chan, f"@{user} {saludo}")
        else:
            USUARIOS_SALUDADOS.add(user_lower)

        # Guardamos que ya fue saludado
        USUARIOS_SALUDADOS.add(user_lower)


frases_patas = [
    "Me tapo los ojitos 🫣.",
    "Link solo para guerreros de temple duro.",
    "Patas, las esposas de los patos wajajá. Ok me callo *v*"
]

def cmd_patas(conn, chan, user, prompt):
    frase_random = random.choice(frases_patas)
    conn.privmsg(chan, f'{frase_random}')

def cmd_oye(conn, chan, user, prompt):
    if not prompt.strip():
        conn.privmsg(chan, f"{user}, debes pedirme/preguntarme algo. Ejemplo: !woye ¿Cómo estás?")
        return
    contexto_canal = DATOS_CANAL.get(CHANNEL, "")
    emocion = EMOCIONES.get(PERSONALIDAD_ACTUAL.get(CHANNEL, "feliz"), EMOCIONES["feliz"])
    preprompt = f"Personalidad: {SYSTEM_PROMPT} Estado emocional: {emocion} Debes responder a la siguiente petición/pregunta en menos de 30 palabras, (procura responder de acuerdo al tipo de pregunta/petición, sé informativo (y simple) cuando la petición lo amerite, cuando sea una consulta casual debes responder como un usuario amistoso de internet, PREGUNTA/PETICIÓN: "
    respuesta = query_gemini(f"{preprompt} {prompt}")
    if respuesta:
        respuesta_corta = respuesta.strip().replace("\n", " ")[:400]
        conn.privmsg(chan, f"@{user} {respuesta_corta}")
        print(f"@{user} {respuesta_corta}")

def cmd_describe(conn, chan, user, prompt):
    respuesta = query_gemini(
        prompt="Di lo linda que luce esta persona de acuerdo al outfit que lleva, incluyendo posibles accesorios, si es que tiene. Por favor procura que la respuesta sea natural y tenga menos de 40 palabras.",
        img_url=f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{CHANNEL}.jpg"
    )
    if respuesta:
        print(f"{respuesta}")
        conn.privmsg(chan, f"{respuesta}")

COMMANDS = {
    '!wping': {'func': cmd_ping, 'roles': ['bronce', 'plata', 'oro']},
    '!woye': {'func': cmd_oye, 'roles': ['bronce', 'plata', 'oro']},
    '!wdescribe': {'func': cmd_describe, 'roles': ['oro']},
    '!wpresentate': {'func': cmd_presentacion, 'roles': ['oro']},
    '!wperso': {'func': cmd_personalidad, 'roles': ['oro']},
    '!patas': {'func': cmd_patas, 'roles': ['bronce', 'plata', 'oro']},
    '!wcomando': {'func': cmd_crearcomando, 'roles': ['oro']},
    '!hervidor': {'func': cmd_hervidor, 'roles': ['bronce', 'plata', 'oro']},
}

def get_user_role(nick: str) -> str:
    nick = nick.lower()
    if nick in [u.lower() for u in USER_ROLES.get('oro', [])]:
        return 'oro'
    elif nick in [u.lower() for u in USER_ROLES.get('plata', [])]:
        return 'plata'
    else:
        return 'bronce'

def handle_command(connection, channel, nick, message):
    saludar_usuario(connection, channel, nick)

    parts = message.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()
    prompt = " ".join(parts[1:])

    if cmd.startswith("@alphonse_bot7"):
        cmd = '!woye'

    if cmd in COMMANDS:
        role = get_user_role(nick)
        allowed_roles = COMMANDS[cmd]['roles']
        if role in allowed_roles:
            COMMANDS[cmd]['func'](connection, channel, nick, prompt)
        else:
            print(f"⛔ {nick} ({role}) no tiene permiso para usar {cmd}")
    elif cmd in CUSTOM_COMMANDS:
        connection.privmsg(channel, CUSTOM_COMMANDS[cmd])
