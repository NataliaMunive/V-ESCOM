"""
Modelo de Datos: Entradas - V-ESCOM

Define los puntos de acceso específicos vinculando cámaras y cubículos.
Permite una descripción textual del lugar exacto del evento de seguridad.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from app.bd import Base

class Entrada(Base):
    """
    Entidad que representa un punto de monitoreo o acceso físico.
    
    Sirve como capa intermedia para dar contexto a los eventos:
    En lugar de solo saber que fue la 'Cámara 5', el sistema puede reportar que el evento ocurrió en la 'Entrada Lateral' del 'Cubículo 10'.
    """
    __tablename__ = "entradas"

    # Identificador único del punto de entrada
    id_entrada = Column(Integer, primary_key=True, index=True)
    
    # Vinculación con el hardware de captura
    id_camara = Column(Integer, ForeignKey("camaras.id_camara"), nullable=True)
    
    # Vinculación con el espacio físico monitoreado
    id_cubiculo = Column(Integer, ForeignKey("cubiculos.id_cubiculo"), nullable=True)
    
    # Nombre descriptivo del punto de acceso (ej. 'Puerta Principal', 'Pasillo A')
    nombre = Column(String(100), nullable=True)
    
    # Categorización del acceso (ej. 'Peatonal', 'Vehicular', 'Emergencia')
    tipo = Column(String(30), nullable=True)
    
    # Estado operativo de este punto de acceso específico
    estado = Column(String(20), default="Activa")