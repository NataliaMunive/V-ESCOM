# test_telegram.py
import os
from dotenv import load_dotenv
from app.bd import SessionLocal
from app.models.administrador import Administrador
from app.services.notificacion_service import enviar_alerta_telegram

# 1. Cargar variables de entorno desde el .env
load_dotenv()

def test_telegram_connection():
    print("--- INICIANDO PRUEBA DE TELEGRAM ---")
    
    # Diagnóstico de configuración
    token = os.getenv("TELEGRAM_TOKEN")
    print(f"Configuración detectada:")
    print(f" - TELEGRAM_TOKEN presente: {'SÍ' if token else 'NO'}")
    
    if not token:
        print("❌ ERROR: TELEGRAM_TOKEN no encontrado en el archivo .env")
        return

    db = SessionLocal()
    try:
        # 2. Consultar administradores con ID configurado
        admins = db.query(Administrador).filter(Administrador.telegram_chat_id.isnot(None)).all()
        
        if not admins:
            print("❌ No hay administradores con 'telegram_chat_id' configurado en la base de datos.")
            return

        print(f"✅ Encontrados {len(admins)} administradores con Telegram configurado.")

        # 3. Intentar el envío
        for admin in admins:
            print(f"Intentando enviar mensaje a: {admin.nombre} (ID: {admin.telegram_chat_id})")
            
            # Llamada al servicio
            resultado = enviar_alerta_telegram(
                mensaje="🤖 Sistema V-ESCOM: Esta es una prueba de conexión manual.",
                ruta_imagen=None,
                chat_id=admin.telegram_chat_id
            )
            
            # Verificación del resultado real
            if resultado is True:
                print(f"✅ ÉXITO: Mensaje entregado correctamente a {admin.nombre}")
            else:
                print(f"❌ FALLO: El servicio de notificación devolvió False. Revisa el log de errores.")

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado al ejecutar el test: {e}")
    finally:
        db.close()
        print("--- PRUEBA FINALIZADA ---")

if __name__ == "__main__":
    test_telegram_connection()