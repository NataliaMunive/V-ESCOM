from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.bd import get_db
from app.models.administrador import Administrador

router = APIRouter()

@router.post("/telegram-webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    # Telegram envía los mensajes en este formato
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        
        # Si el admin escribe "/start ID_USUARIO" (o algo para identificarse)
        # Aquí puedes implementar lógica para buscar al admin por email y guardar su chat_id
        if text.startswith("/register "):
            email = text.split(" ")[1]
            admin = db.query(Administrador).filter(Administrador.email == email).first()
            if admin:
                admin.telegram_chat_id = str(chat_id)
                db.commit()
                return {"status": "Registrado correctamente"}
    
    return {"status": "ok"}