from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.config import Configuracion
from app.dependencies import obtener_configuracion, obtener_sesion
from app.dto.auth import TokenAcceso
from app.schemas.auth import Credenciales
from app.services.auth_service import iniciar_sesion


router = APIRouter()

EJEMPLO_LOGIN = {
    "credenciales": {
        "summary": "Credenciales de RescueSync",
        "description": (
            "Usar el usuario y la contraseña definidos en `USUARIO_RESCUESYNC` y "
            "`PASSWORD_RESCUESYNC` del `.env`."
        ),
        "value": {"usuario": "usuario-rescuesync", "password": "password"},
    }
}


@router.post(
    "/login",
    response_model=TokenAcceso,
    summary="Iniciar sesión y obtener el JWT",
    description=(
        "Primer paso para probar los endpoints protegidos. Copiá el `access_token` de la "
        "respuesta y pegalo en el botón **Authorize** de Swagger."
    ),
    responses={
        200: {
            "description": "Token emitido",
            "content": {"application/json": {"example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
            }}},
        },
        401: {
            "description": "Credenciales inválidas",
            "content": {"application/json": {"example": {"detail": "Credenciales inválidas"}}},
        },
        503: {
            "description": "Falta configuración o la base no está disponible",
            "content": {"application/json": {"example": {
                "detail": "Configurar DATABASE_URL y JWT_SECRET para usar este servicio",
            }}},
        },
    },
)
def login(
    datos: Credenciales = Body(openapi_examples=EJEMPLO_LOGIN),
    db: Session = Depends(obtener_sesion),
    configuracion: Configuracion = Depends(obtener_configuracion),
):
    return iniciar_sesion(db, datos, configuracion)
