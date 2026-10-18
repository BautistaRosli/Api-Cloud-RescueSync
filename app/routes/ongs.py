from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import obtener_cuenta, obtener_sesion
from app.dto.ong import OngCreada
from app.schemas.ong import RegistroOng
from app.services.ongs_service import registrar_ong


router = APIRouter(dependencies=[Depends(obtener_cuenta)])


@router.post("/registro", response_model=OngCreada, status_code=201)
def registro(datos: RegistroOng, db: Session = Depends(obtener_sesion)):
    return registrar_ong(db, datos)
