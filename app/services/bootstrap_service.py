from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import Configuracion
from app.models import Cuenta


def asegurar_cuenta_rescuesync(sesiones: sessionmaker, configuracion: Configuracion) -> None:
    try:
        with sesiones.begin() as sesion:
            cuenta = sesion.scalar(select(Cuenta).where(Cuenta.usuario == configuracion.usuario_rescuesync))
            if cuenta is None:
                sesion.add(Cuenta(
                    usuario=configuracion.usuario_rescuesync,
                    password_hash=configuracion.password_hash_rescuesync,
                ))
    except Exception:
        raise RuntimeError("No se pudo inicializar la cuenta de RescueSync") from None
