from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Configuracion
from app.dependencies import obtener_configuracion, obtener_sesion
from app.dto.auth import CuentaCreada, TokenAcceso
from app.schemas.auth import Credenciales
from app.services.auth_service import iniciar_sesion, registrar_cuenta


router = APIRouter()


@router.post("/registro", response_model=CuentaCreada, status_code=201)
def registro(datos: Credenciales, db: Session = Depends(obtener_sesion)):
    return registrar_cuenta(db, datos)


@router.post("/login", response_model=TokenAcceso)
def login(
    datos: Credenciales,
    db: Session = Depends(obtener_sesion),
    configuracion: Configuracion = Depends(obtener_configuracion),
):
    return iniciar_sesion(db, datos, configuracion)
