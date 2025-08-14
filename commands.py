from config import EMOCIONES, DATOS_CANAL, SYSTEM_PROMPT, PERSONALIDAD_ACTUAL, CHANNEL, USER_ROLES
from gemini import query_gemini

def cmd_ping(conn, chan, user, prompt):
    conn.privmsg(chan, f'{user}, pong!')
    print(f'@{user} pong!')

def cmd_personalidad(conn, chan, user, prompt):
    if not prompt.strip():
        conn.privmsg(chan, f"{user}, debes indicar una personalidad. Ej: !wperso triste")
        return
    tipo = prompt.strip().lower()
    if tipo in EMOCIONES:
        PERSONALIDAD_ACTUAL[CHANNEL] = tipo
        print(f"🔄 Personalidad de {CHANNEL}: {tipo}")

def cmd_presentacion(conn, chan, user, prompt):
    print('Hoolas * se presenta *')

def cmd_oye(conn, chan, user, prompt):
    if not prompt.strip():
        conn.privmsg(chan, f"{user}, debes pedirme/preguntarme algo. Ejemplo: !woye ¿Cómo estás?")
        return
    contexto_canal = DATOS_CANAL.get(CHANNEL, "")
    emocion = EMOCIONES.get(PERSONALIDAD_ACTUAL.get(CHANNEL, "feliz"), EMOCIONES["feliz"])
    preprompt = f"Personalidad: {SYSTEM_PROMPT} Estado emocional: {emocion} Debes responder a la siguiente petición/pregunta en menos de 30 palabras (importante): "
    respuesta = query_gemini(f"{preprompt} {prompt}")
    if respuesta:
        respuesta_corta = respuesta.strip().replace("\n", " ")[:400]
        conn.privmsg(chan, f"@{user} {respuesta_corta}")
        print(f"@{user} {respuesta_corta}")

def cmd_describe(conn, chan, user, prompt):
    respuesta = query_gemini(
        prompt="Di lo linda que luce esta persona de acuerdo al outfit que lleva, por favor procura que la respuesta sea natural y tenga menos de 40 palabras.",
        img_url=f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{CHANNEL}.jpg"
    )
    if respuesta:
        print(f"{respuesta}")
        conn.privmsg(chan, f"{respuesta}")

COMMANDS = {
    '!wping': {'func': cmd_ping, 'roles': ['bronce', 'plata', 'oro']},
    '!woye': {'func': cmd_oye, 'roles': ['oro']},
    '!wdescribe': {'func': cmd_describe, 'roles': ['oro']},
    '!wpresentate': {'func': cmd_presentacion, 'roles': ['oro']},
    '!wperso': {'func': cmd_personalidad, 'roles': ['oro']}
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
    parts = message.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()
    prompt = " ".join(parts[1:])
    if cmd in COMMANDS:
        role = get_user_role(nick)
        allowed_roles = COMMANDS[cmd]['roles']
        if role in allowed_roles:
            COMMANDS[cmd]['func'](connection, channel, nick, prompt)
        else:
            print(f"⛔ {nick} ({role}) no tiene permiso para usar {cmd}")
