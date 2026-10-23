from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import Configuracion
from app.models import Cuenta
from app.services.auth_service import generar_hash


def asegurar_cuenta_rescuesync(sesiones: sessionmaker, configuracion: Configuracion) -> None:
    try:
        password_hash = generar_hash(configuracion.password_rescuesync)
        with sesiones.begin() as sesion:
            cuentas = sesion.scalars(select(Cuenta).order_by(Cuenta.id)).all()
            cuenta = next(
                (cuenta for cuenta in cuentas if cuenta.usuario == configuracion.usuario_rescuesync),
                cuentas[0] if cuentas else None,
            )
            if cuenta is None:
                sesion.add(Cuenta(
                    usuario=configuracion.usuario_rescuesync,
                    password_hash=password_hash,
                ))
            else:
                cuenta.usuario = configuracion.usuario_rescuesync
                cuenta.password_hash = password_hash
                for otra_cuenta in cuentas:
                    if otra_cuenta is not cuenta:
                        sesion.delete(otra_cuenta)
    except Exception:
        raise RuntimeError("No se pudo inicializar la cuenta de RescueSync") from None
