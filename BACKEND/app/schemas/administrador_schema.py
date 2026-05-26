from pydantic import BaseModel
from typing import Optional

class AdministradorUpdate(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    telegram_chat_id: Optional[str] = None