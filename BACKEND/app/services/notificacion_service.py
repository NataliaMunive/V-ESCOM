import os
import requests
from dotenv import load_dotenv

load_dotenv()

def enviar_alerta_telegram(mensaje: str, ruta_imagen: str = None):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    target_chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    
    # URL base para la API de Telegram
    base_url = f"https://api.telegram.org/bot{token}"
    
    try:
        # Si hay una imagen, enviamos una foto
        if ruta_imagen and os.path.exists(ruta_imagen):
            url = f"{base_url}/sendPhoto"
            files = {'photo': open(ruta_imagen, 'rb')}
            data = {'chat_id': chat_id, 'caption': mensaje}
            response = requests.post(url, data=data, files=files)
        else:
            # Si es solo texto
            url = f"{base_url}/sendMessage"
            data = {'chat_id': chat_id, 'text': mensaje}
            response = requests.post(url, data=data)
            
        return response.status_code == 200
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")
        return False