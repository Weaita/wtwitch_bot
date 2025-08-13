import requests
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from config import JSONBIN_ID, JSONBIN_API_KEY, SCOPES, CLIENT_ID, CLIENT_SECRET, CHANNEL

JSONBIN_URL = f'https://api.jsonbin.io/v3/b/{JSONBIN_ID}'
HEADERS = {
    'X-Master-Key': JSONBIN_API_KEY,
    'Content-Type': 'application/json'
}

def get_tokens():
    response = requests.get(JSONBIN_URL + '/latest', headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    tokens = data['record']
    return tokens.get('access_token', ''), tokens.get('refresh_token', '')

def update_tokens(access_token, refresh_token):
    payload = {
        'access_token': access_token,
        'refresh_token': refresh_token
    }
    response = requests.put(JSONBIN_URL, headers=HEADERS, json=payload)
    response.raise_for_status()
    print("✅ Tokens guardados en JSONBin.")

def refresh_access_token(client_id, client_secret, refresh_token):
    url = 'https://id.twitch.tv/oauth2/token'
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    tokens = response.json()
    return tokens['access_token'], tokens['refresh_token']

async def authenticate_and_store(twitch: Twitch):
    print("🔐 No se encontraron tokens válidos. Abriendo navegador para autenticar...")
    auth = UserAuthenticator(twitch, SCOPES)
    token, refresh_token = await auth.authenticate()
    update_tokens(token, refresh_token)
    return token, refresh_token

def get_app_access_token():
    """Obtiene un app access token de Twitch."""
    url = 'https://id.twitch.tv/oauth2/token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()['access_token']

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
