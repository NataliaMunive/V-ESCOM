# test_telegram.py
from app.bd import SessionLocal
from app.models.administrador import Administrador
from app.services.notificacion_service import enviar_alerta_telegram

def probar_telegram():
    db = SessionLocal()
    try:
        # 1. Obtenemos a todos los administradores que tienen un ID de Telegram
        admins = db.query(Administrador).filter(Administrador.telegram_chat_id.isnot(None)).all()
        
        if not admins:
            print("❌ No hay administradores con 'telegram_chat_id' configurado en la BD.")
            print("   Revisa la BD con la consulta SQL que te proporcioné antes.")
            return

        print(f"✅ Encontrados {len(admins)} administradores con Telegram configurado.")

        # 2. Enviamos un mensaje de prueba a cada uno
        for admin in admins:
            print(f"Enviando prueba a: {admin.nombre} | ID: {admin.telegram_chat_id}")
            
            try:
                # Enviamos el mensaje (ruta_imagen=None porque es solo texto)
                enviar_alerta_telegram(
                    mensaje=f"🤖 Hola {admin.nombre}, esta es una prueba de conexión desde V-ESCOM.",
                    ruta_imagen=None,
                    chat_id=admin.telegram_chat_id
                )
                print(f"✅ Mensaje enviado exitosamente a {admin.nombre}")
            except Exception as e:
                print(f"❌ Error enviando a {admin.nombre}: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    probar_telegram()