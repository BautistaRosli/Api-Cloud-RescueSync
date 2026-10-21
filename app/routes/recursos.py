from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import obtener_cuenta, obtener_sesion
from app.dto.recursos import DisponibilidadTipo
from app.services.recursos_service import calcular_disponibilidad


router = APIRouter(dependencies=[Depends(obtener_cuenta)])


@router.post("/bloquear")
def bloquear() -> str:
    return "Pendiente de implementación"


@router.get(
    "/disponibilidad",
    response_model=list[DisponibilidadTipo],
    summary="Disponibilidad global de recursos por tipo",
    description=(
        "Agrupa el inventario de las ONGs **activas** por tipo de recurso y devuelve, para cada tipo, "
        "la cantidad `total`, la `comprometida` (compromisos en estado BLOQUEADO o COMPROMETIDO) y la "
        "`disponible` (total - comprometido). Se puede filtrar por `tipo_recurso_id` y/o `ong_id`; "
        "si la ONG filtrada no existe o está inactiva, la lista vuelve vacía."
    ),
    responses={
        200: {
            "content": {"application/json": {"example": [
                {"tipo_recurso_id": 101, "nombre": "Paramédicos", "unidad": "personas",
                 "total": 120, "comprometido": 40, "disponible": 80},
                {"tipo_recurso_id": 105, "nombre": "Camiones", "unidad": "unidades",
                 "total": 23, "comprometido": 5, "disponible": 18},
            ]}}
        }
    },
)
def disponibilidad(
    tipo_recurso_id: int | None = Query(None, ge=1, description="Solo este tipo de recurso (id del catálogo de items)"),
    ong_id: int | None = Query(None, ge=1, description="Solo el inventario de esta ONG"),
    db: Session = Depends(obtener_sesion),
):
    return calcular_disponibilidad(db, tipo_recurso_id, ong_id)
