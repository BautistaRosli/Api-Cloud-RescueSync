import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Configuracion:
    database_url: str
    jwt_secret: str
    duracion_token: int = 3600
    jwt_issuer: str = "rescuesync-cloud"
    jwt_audience: str = "rescuesync-cloud"
    jwt_backend_audience: str = "rescuesync-backend"
    usuario_rescuesync: str = ""
    password_rescuesync: str = field(default="", repr=False)


def cargar_configuracion() -> Configuracion | None:
    database_url = os.getenv("DATABASE_URL", "")
    jwt_secret = os.getenv("JWT_SECRET", "")
    if not database_url.strip() or not jwt_secret.strip():
        return None
    usuario_rescuesync = os.getenv("USUARIO_RESCUESYNC", "")
    password_rescuesync = os.getenv("PASSWORD_RESCUESYNC", "")
    if not usuario_rescuesync.strip() or not password_rescuesync.strip():
        raise RuntimeError("Definir USUARIO_RESCUESYNC y PASSWORD_RESCUESYNC")
    return Configuracion(
        database_url=database_url,
        jwt_secret=jwt_secret,
        jwt_issuer=os.getenv("JWT_ISSUER", "rescuesync-cloud"),
        jwt_audience=os.getenv("JWT_AUDIENCE", "rescuesync-cloud"),
        jwt_backend_audience=os.getenv("JWT_BACKEND_AUDIENCE", "rescuesync-backend"),
        usuario_rescuesync=usuario_rescuesync,
        password_rescuesync=password_rescuesync,
    )
