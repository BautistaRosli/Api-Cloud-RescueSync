from fastapi import APIRouter, Depends

from app.dependencies import obtener_cuenta


router = APIRouter(dependencies=[Depends(obtener_cuenta)])


@router.post("/evaluar-ofertas")
def evaluar_ofertas() -> str:
    return "Pendiente de implementación"
