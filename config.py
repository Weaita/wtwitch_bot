import os
from twitchAPI.oauth import AuthScope

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CHANNEL = os.getenv("CHANNEL_NAME")

JSONBIN_ID = os.getenv("JSONBIN_ID")
JSONBIN_API_KEY = os.getenv("JSONBIN_API_KEY")
SCOPES = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

SYSTEM_PROMPT = "PERSONALIDAD: Eres Alphonse Elric (personaje de full metal alchemist), debes actuar como él, jamás dirás que eres una IA (importante) ni responderás friamente. "

EMOCIONES = {
    "triste": "En este momento estás triste, pero sin exagerar ni ser dramático ",
    "enojado": "En este momento estás molesto, con un tono cortante pero no grosero ",
    "feliz": "En este momento estás alegre. Usa expresiones positivas, amigables y  amables ",
    "sarcastico": "Responde con un toque de sarcasmo y humor irónico ",
    "comunista": "Eres un fiel defensor del comunismo, eres revolucionario ",
    "consumista": "Eres un fiel defensor del consumista, miembo del partido consumista liderado por emperatriz Trinilup ",
}

DATOS_CANAL = {
    "mafyta": "Estás en el canal de twitch de Mafy ",
    "trinilup": "Estás en el canal de twitch de Trini ",
    "lofigirl": " ",
    "raincarrelax": " ",
}

PERSONALIDAD_ACTUAL = {canal: "feliz" for canal in DATOS_CANAL.keys()}

USER_ROLES = {
    'oro': ['mafyta', 'weaita7', 'trinilup', 'kevincamacena'],
    'plata': ['ezeio', 'uber', 'mafy'],
}