"""
Servicio de Auditoría y Trazabilidad - V-ESCOM

Proporciona una interfaz unificada para registrar eventos operativos, errores 
técnicos y actividades de seguridad en la bitácora del sistema (logs_sistema).
"""

from sqlalchemy.orm import Session
from app.models.log_sistema import LogSistema


def registrar_log(
    db: Session,
    *,
    mensaje: str,
    nivel: str = "INFO",
    origen: str = "Sistema",
    tipo: str = "Sistema",
    id_evento: int | None = None,
    commit: bool = False,
) -> None:
    """
    Registra una entrada en el log del sistema de forma segura.
    
    Args:
        mensaje: Descripción detallada del suceso.
        nivel: Gravedad (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        origen: Componente que emite el log (ej: 'Servicio_SMS').
        tipo: Categoría del evento (ej: 'Autenticación', 'IA').
        id_evento: Relación opcional con un evento de acceso específico.
        commit: Si es True, confirma la transacción inmediatamente.
    """
    try:
        # Creamos la instancia del log vinculándola opcionalmente a un evento físico
        nuevo_log = LogSistema(
            id_evento=id_evento,
            nivel=nivel,
            origen=origen,
            tipo=tipo,
            mensaje=mensaje,
        )
        db.add(nuevo_log)
        
        # El commit opcional permite agrupar logs con otras operaciones de base de datos
        if commit:
            db.commit()
            
    except Exception:
        # Estrategia de resiliencia: Si el registro de auditoría falla (ej. DB saturada),
        # no permitimos que la excepción detenga el proceso de negocio principal.
        pass