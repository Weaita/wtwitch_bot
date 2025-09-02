import requests
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from config import JSONBIN_ID, JSONBIN_API_KEY, SCOPES, CLIENT_ID, CLIENT_SECRET, CHANNEL

JSONBIN_URL = f'https://api.jsonbin.io/v3/b/{JSONBIN_ID}'
HEADERS = {
    'X-Master-Key': JSONBIN_API_KEY,
    'Content-Type': 'application/json'
}

# obtener los tokens de acceso y actualización guardados en JSONBinJSONBIN
def get_tokens():
    response = requests.get(JSONBIN_URL + '/latest', headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    tokens = data['record']
    return tokens.get('access_token', ''), tokens.get('refresh_token', '')

# actualizar los tokens en JSONBIN
def saveTokensToJSONBIN(access_token, refresh_token):
    payload = {
        'access_token': access_token,
        'refresh_token': refresh_token
    }
    response = requests.put(JSONBIN_URL, headers=HEADERS, json=payload)
    response.raise_for_status()
    print("[TOKENS.py] Tokens guardados en JSONBin.")

# renovar access token usando refresh token
def refresh_access_token(client_id, client_secret, refresh_token, save_to_db=True):
    url = 'https://id.twitch.tv/oauth2/token'
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        new_access = tokens['access_token']
        new_refresh = tokens['refresh_token']
        expires_in = tokens['expires_in']

        # Guardar los tokens actualizados
        if save_to_db:
            saveTokensToJSONBIN(new_access, new_refresh)
            print("[TOKENS.py] ☁️ Tokens guardados en dB")

        print("[TOKENS.py] 🔄 Tokens refrescados correctamente")
        return new_access, new_refresh, expires_in
    else:
        print("[TOKENS.py] ❌ Error refrescando tokens:", response.json())
        return None, None, None

# generar nuevos tokens mediante autenticación de usuario
async def authenticate_and_store(twitch: Twitch):
    auth = UserAuthenticator(twitch, SCOPES)
    token, refresh_token = await auth.authenticate()
    saveTokensToJSONBIN(token, refresh_token)
    return token, refresh_token

# Verifica si los tokens son válidos
def verify_tokens(access_token):
    """Devuelve True si el access_token es válido, False si no"""
    try:
        resp = requests.get(
            "https://id.twitch.tv/oauth2/validate",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code == 200:
            print("[TOKENS.py] ✅ Access token válido")
            return True
        else:
            print("[TOKENS.py] ⚠️ Access token inválido o caducado")
            return False
    except Exception as e:
        print("[TOKENS.py] ❌ Error verificando access token:", e)
        return False


# utilidades
# obtener broadcaster_id del canal
def get_broadcaster_id(token):
    """Obtiene el broadcaster_id del canal."""
    url = 'https://api.twitch.tv/helix/users'
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    params = {'login': CHANNEL}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return data['data'][0]['id']

# verificar si canal está en vivo
def is_channel_live(token):
    """Verifica si el canal está en vivo."""
    url = 'https://api.twitch.tv/helix/streams'
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    params = {'user_login': CHANNEL}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return len(data['data']) > 0