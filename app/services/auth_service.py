import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Configuracion
from app.dto.auth import CuentaCreada, TokenAcceso
from app.models import Cuenta
from app.schemas.auth import Credenciales


ITERACIONES = 600_000
ALGORITMO_JWT = "HS256"


def generar_hash(password: str) -> str:
    sal = secrets.token_hex(16)
    resumen = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal}${resumen.hex()}"


def verificar_password(password: str, password_hash: str) -> bool:
    _, iteraciones, sal, esperado = password_hash.split("$")
    resumen = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), int(iteraciones))
    return hmac.compare_digest(resumen.hex(), esperado)


def credenciales_invalidas() -> HTTPException:
    return HTTPException(status_code=401, detail="Credenciales inválidas", headers={"WWW-Authenticate": "Bearer"})


def registrar_cuenta(db: Session, datos: Credenciales) -> CuentaCreada:
    cuenta = Cuenta(usuario=datos.usuario, password_hash=generar_hash(datos.password.get_secret_value()))
    db.add(cuenta)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El usuario ya está registrado") from None
    return CuentaCreada.model_validate(cuenta)


def iniciar_sesion(db: Session, datos: Credenciales, configuracion: Configuracion) -> TokenAcceso:
    cuenta = db.scalar(select(Cuenta).where(Cuenta.usuario == datos.usuario))
    if cuenta is None:
        generar_hash(datos.password.get_secret_value())
        raise credenciales_invalidas()
    if not verificar_password(datos.password.get_secret_value(), cuenta.password_hash):
        raise credenciales_invalidas()
    ahora = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(cuenta.id),
            "usuario": cuenta.usuario,
            "iss": configuracion.jwt_issuer,
            "aud": [configuracion.jwt_audience, configuracion.jwt_backend_audience],
            "iat": ahora,
            "exp": ahora + timedelta(seconds=configuracion.duracion_token),
        },
        configuracion.jwt_secret,
        algorithm=ALGORITMO_JWT,
    )
    return TokenAcceso(access_token=token, expires_in=configuracion.duracion_token)


def autenticar_token(db: Session, token: str, configuracion: Configuracion) -> Cuenta:
    try:
        datos = jwt.decode(
            token,
            configuracion.jwt_secret,
            algorithms=[ALGORITMO_JWT],
            issuer=configuracion.jwt_issuer,
            audience=configuracion.jwt_audience,
            options={"require": ["sub", "usuario", "iat", "exp", "iss", "aud"]},
        )
        identificador = int(datos["sub"])
        if identificador < 1 or not isinstance(datos["usuario"], str) or not datos["usuario"].strip():
            raise ValueError
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise credenciales_invalidas() from None
    cuenta = db.get(Cuenta, identificador)
    if cuenta is None or cuenta.usuario != datos["usuario"]:
        raise credenciales_invalidas()
    return cuenta
