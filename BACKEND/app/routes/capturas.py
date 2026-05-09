"""
Router de Capturas de Intrusos - V-ESCOM
Sirve las imágenes guardadas en capturas_intrusos/
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.models.evento import PersonaNoAutorizada

router = APIRouter(prefix="/capturas", tags=["Capturas de Intrusos"])

DIRECTORIO = os.getenv("DIRECTORIO_INTRUSOS", "capturas_intrusos")


@router.get("/intruso/{id_evento}", summary="Obtener imagen de captura del intruso")
def obtener_captura(
    id_evento: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """
    Devuelve la imagen JPG capturada cuando se detectó la intrusión.
    Se busca en personas_no_autorizadas por id_evento via alertas.
    """
    from app.models.alerta import Alerta
    from app.models.evento import EventoAcceso

    # Buscar evento
    evento = db.query(EventoAcceso).filter(
        EventoAcceso.id_evento == id_evento
    ).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    # Buscar captura en personas_no_autorizadas por fecha/hora aproximada
    pna = db.query(PersonaNoAutorizada).filter(
        PersonaNoAutorizada.ruta_imagen_captura.isnot(None)
    ).order_by(PersonaNoAutorizada.id_pna.desc()).first()

    # Intentar encontrar la más cercana al evento
    pnas = db.query(PersonaNoAutorizada).filter(
        PersonaNoAutorizada.ruta_imagen_captura.isnot(None),
        PersonaNoAutorizada.fecha == evento.fecha,
    ).all()

    ruta = None
    if pnas:
        # Tomar la más cercana en hora
        for p in pnas:
            if p.ruta_imagen_captura and os.path.exists(p.ruta_imagen_captura):
                ruta = p.ruta_imagen_captura
                break

    # Fallback: buscar por nombre de archivo con id_evento
    if not ruta:
        if os.path.exists(DIRECTORIO):
            for archivo in sorted(os.listdir(DIRECTORIO), reverse=True):
                ruta_candidata = os.path.join(DIRECTORIO, archivo)
                if os.path.exists(ruta_candidata):
                    ruta = ruta_candidata
                    break

    if not ruta or not os.path.exists(ruta):
        raise HTTPException(
            status_code=404,
            detail="No se encontró imagen para este evento"
        )

    return FileResponse(ruta, media_type="image/jpeg")


@router.get("/intruso/alerta/{id_alerta}", summary="Obtener imagen por ID de alerta")
def obtener_captura_por_alerta(
    id_alerta: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """Devuelve la imagen JPG asociada a una alerta específica."""
    from app.models.alerta import Alerta

    alerta = db.query(Alerta).filter(Alerta.id_alerta == id_alerta).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    return obtener_captura(alerta.id_evento, db, _admin)