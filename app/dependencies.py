from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Configuracion
from app.models import Cuenta
from app.services.auth_service import autenticar_token, credenciales_invalidas


portador = HTTPBearer(auto_error=False)


def obtener_configuracion(request: Request) -> Configuracion:
    configuracion = request.app.state.configuracion
    if configuracion is None:
        raise HTTPException(status_code=503, detail="Configurar DATABASE_URL y JWT_SECRET para usar este servicio")
    return configuracion


def obtener_sesion(request: Request, configuracion: Configuracion = Depends(obtener_configuracion)):
    with request.app.state.sesiones() as sesion:
        yield sesion


def obtener_cuenta(
    credenciales: HTTPAuthorizationCredentials | None = Depends(portador),
    db: Session = Depends(obtener_sesion),
    configuracion: Configuracion = Depends(obtener_configuracion),
) -> Cuenta:
    if credenciales is None:
        raise credenciales_invalidas()
    return autenticar_token(db, credenciales.credentials, configuracion)
