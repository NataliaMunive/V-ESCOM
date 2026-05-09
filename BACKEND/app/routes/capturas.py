"""
Router de Capturas de Intrusos - V-ESCOM
Sirve las imágenes guardadas en capturas_intrusos/ vinculadas correctamente
a cada evento/alerta específica.
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.bd import get_db
from app.core.deps import get_current_admin
from app.models.administrador import Administrador
from app.models.alerta import Alerta
from app.models.evento import EventoAcceso, PersonaNoAutorizada

router = APIRouter(prefix="/capturas", tags=["Capturas de Intrusos"])

DIRECTORIO = os.getenv("DIRECTORIO_INTRUSOS", "capturas_intrusos")


def _buscar_imagen_por_evento(db: Session, id_evento: int) -> str | None:
    """
    Estrategia de búsqueda en orden de prioridad:
    1. Buscar en personas_no_autorizadas por fecha y hora más cercana al evento.
    2. Buscar por nombre de archivo que contenga el id_evento.
    3. Fallback: imagen más reciente del directorio.
    """
    evento = db.query(EventoAcceso).filter(
        EventoAcceso.id_evento == id_evento
    ).first()

    if not evento:
        return None

    # Estrategia 1: buscar PNA con misma fecha y hora más cercana
    if evento.fecha and evento.hora:
        pnas = (
            db.query(PersonaNoAutorizada)
            .filter(
                PersonaNoAutorizada.ruta_imagen_captura.isnot(None),
                PersonaNoAutorizada.fecha == evento.fecha,
            )
            .all()
        )

        # Encontrar la PNA cuya hora sea más cercana a la del evento
        mejor = None
        menor_diff = None

        for pna in pnas:
            if not pna.ruta_imagen_captura:
                continue
            if not os.path.exists(pna.ruta_imagen_captura):
                continue
            if pna.hora and evento.hora:
                # Calcular diferencia en segundos
                from datetime import datetime, date
                t_pna    = datetime.combine(date.today(), pna.hora)
                t_evento = datetime.combine(date.today(), evento.hora)
                diff = abs((t_pna - t_evento).total_seconds())
                if menor_diff is None or diff < menor_diff:
                    menor_diff = diff
                    mejor = pna.ruta_imagen_captura

        # Solo aceptar si la diferencia es menor a 10 segundos
        if mejor and menor_diff is not None and menor_diff <= 10:
            return mejor

    # Estrategia 2: buscar archivo con id_evento en el nombre
    if os.path.exists(DIRECTORIO):
        for archivo in os.listdir(DIRECTORIO):
            if str(id_evento) in archivo:
                ruta = os.path.join(DIRECTORIO, archivo)
                if os.path.exists(ruta):
                    return ruta

    # Estrategia 3: imagen más reciente (fallback)
    if os.path.exists(DIRECTORIO):
        archivos = [
            f for f in os.listdir(DIRECTORIO)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
        if archivos:
            archivos.sort(reverse=True)
            ruta = os.path.join(DIRECTORIO, archivos[0])
            if os.path.exists(ruta):
                return ruta

    return None


@router.get("/intruso/alerta/{id_alerta}", summary="Imagen del intruso por ID de alerta")
def obtener_captura_por_alerta(
    id_alerta: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """Devuelve la imagen JPG del intruso asociada a una alerta específica."""
    alerta = db.query(Alerta).filter(Alerta.id_alerta == id_alerta).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    if not alerta.id_evento:
        raise HTTPException(status_code=404, detail="La alerta no tiene evento asociado")

    ruta = _buscar_imagen_por_evento(db, alerta.id_evento)

    if not ruta:
        raise HTTPException(
            status_code=404,
            detail="No se encontró imagen para esta alerta"
        )

    return FileResponse(
        ruta,
        media_type="image/jpeg",
        filename=f"intruso_alerta_{id_alerta}.jpg"
    )


@router.get("/intruso/evento/{id_evento}", summary="Imagen del intruso por ID de evento")
def obtener_captura_por_evento(
    id_evento: int,
    db: Session = Depends(get_db),
    _admin: Administrador = Depends(get_current_admin),
):
    """Devuelve la imagen JPG del intruso asociada a un evento específico."""
    ruta = _buscar_imagen_por_evento(db, id_evento)

    if not ruta:
        raise HTTPException(
            status_code=404,
            detail="No se encontró imagen para este evento"
        )

    return FileResponse(
        ruta,
        media_type="image/jpeg",
        filename=f"intruso_evento_{id_evento}.jpg"
    )