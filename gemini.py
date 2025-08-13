import requests
import base64
from config import GEMINI_API_KEY, GEMINI_ENDPOINT

def query_gemini(prompt: str, img_url: str = None) -> str:
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }

    parts = []
    if img_url:
        try:
            response = requests.get(img_url)
            response.raise_for_status()
            mime_type = response.headers.get("Content-Type", "image/jpeg")
            image_data = base64.b64encode(response.content).decode("utf-8")

            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": image_data
                }
            })
        except Exception as e:
            print("❌ Error al descargar o procesar la imagen:", e)
            return

    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}]
    }

    response = requests.post(GEMINI_ENDPOINT, headers=headers, json=payload)

    if response.status_code != 200:
        print("❌ Error al consultar Gemini:", response.status_code, response.text)
        return

    try:
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("⚠️ Respuesta inesperada:", data)
        return
