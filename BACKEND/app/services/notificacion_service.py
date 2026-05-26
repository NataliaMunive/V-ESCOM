# app/services/notificacion_service.py
import os
import requests # O la librería que uses para Telegram

def enviar_alerta_telegram(mensaje: str, ruta_imagen: str = None, chat_id: str = None):
    """
    Envía un mensaje a Telegram. 
    Si chat_id es proporcionado, se envía a ese usuario.
    Si no, usa el ID por defecto del .env.
    """
    # Usamos el chat_id que recibimos, o si es None, el del .env
    target_chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    token = os.getenv("TELEGRAM_TOKEN")
    
    if not target_chat_id or not token:
        print("Error: Falta configurar TELEGRAM_TOKEN o el chat_id es inválido")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Aquí va tu lógica para enviar el mensaje con requests o la librería que uses
    # Ejemplo básico:
    payload = {
        "chat_id": target_chat_id,
        "text": mensaje
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error en envío Telegram: {e}")
        return False