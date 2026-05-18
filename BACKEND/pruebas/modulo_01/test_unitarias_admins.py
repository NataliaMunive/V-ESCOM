"""
Pruebas Unitarias - Validación de duplicados para administradores
V-ESCOM

Casos cubiertos:
    VESCOM-AUTH-U08: Rechazo de correo duplicado al crear administrador
    VESCOM-AUTH-U09: Rechazo de teléfono duplicado al crear administrador
    VESCOM-AUTH-U10: Rechazo de correo o teléfono duplicado al actualizar administrador

Cómo ejecutar (desde la carpeta BACKEND con el entorno virtual activado):
    .\\venv\\Scripts\\python.exe -m pytest pruebas/modulo_01/test_unitarias_admins.py -v
"""

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.bd import Base
from app.models.administrador import Administrador
from app.schemas.auth_schema import CrearAdmin, UpdAdmin
from app.services import auth_service


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[Administrador.__table__])
    SessionTesting = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine, tables=[Administrador.__table__])


def _crear_admin_base(db_session, *, email, telefono):
    return auth_service.crear_admin(
        db_session,
        CrearAdmin(
            nombre="Admin",
            apellidos="Prueba",
            email=email,
            telefono=telefono,
            contrasena="Admin1234!",
        ),
    )


def test_U08_rechazo_correo_duplicado_en_creacion(db_session):
    _crear_admin_base(db_session, email="admin1@escom.mx", telefono="5512345678")

    with pytest.raises(Exception) as error:
        _crear_admin_base(db_session, email="Admin1@escom.mx", telefono="5510000000")

    assert getattr(error.value, "status_code", None) == 409
    assert "correo" in str(getattr(error.value, "detail", "")).lower()


def test_U09_rechazo_telefono_duplicado_en_creacion(db_session):
    _crear_admin_base(db_session, email="admin1@escom.mx", telefono="55 1234 5678")

    with pytest.raises(Exception) as error:
        _crear_admin_base(db_session, email="admin2@escom.mx", telefono="+52 55 1234 5678")

    assert getattr(error.value, "status_code", None) == 409
    assert "teléfono" in str(getattr(error.value, "detail", "")).lower()


def test_U10_rechazo_correo_o_telefono_duplicado_en_actualizacion(db_session):
    admin_principal = _crear_admin_base(db_session, email="admin1@escom.mx", telefono="5512345678")
    _crear_admin_base(db_session, email="admin2@escom.mx", telefono="5598765432")

    with pytest.raises(Exception) as error_correo:
        auth_service.actualizar_admin(
            db_session,
            admin_principal.id_admin,
            UpdAdmin(email="ADMIN2@escom.mx"),
        )

    assert getattr(error_correo.value, "status_code", None) == 409
    assert "correo" in str(getattr(error_correo.value, "detail", "")).lower()

    with pytest.raises(Exception) as error_telefono:
        auth_service.actualizar_admin(
            db_session,
            admin_principal.id_admin,
            UpdAdmin(telefono="+52 55 9876 5432"),
        )

    assert getattr(error_telefono.value, "status_code", None) == 409
    assert "teléfono" in str(getattr(error_telefono.value, "detail", "")).lower()