from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Configuracion
from app.dependencies import obtener_configuracion, obtener_sesion
from app.dto.auth import TokenAcceso
from app.schemas.auth import Credenciales
from app.services.auth_service import iniciar_sesion


router = APIRouter()


@router.post("/login", response_model=TokenAcceso)
def login(
    datos: Credenciales,
    db: Session = Depends(obtener_sesion),
    configuracion: Configuracion = Depends(obtener_configuracion),
):
    return iniciar_sesion(db, datos, configuracion)
