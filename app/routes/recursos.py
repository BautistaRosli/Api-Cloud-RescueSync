from fastapi import APIRouter, Depends

from app.dependencies import obtener_cuenta


router = APIRouter(dependencies=[Depends(obtener_cuenta)])


@router.post("/bloquear")
def bloquear() -> str:
    return "Pendiente de implementación"


@router.get("/disponibilidad")
def disponibilidad() -> str:
    return "Pendiente de implementación"
