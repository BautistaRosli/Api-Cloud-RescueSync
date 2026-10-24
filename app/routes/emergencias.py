from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.dependencies import obtener_cuenta, obtener_sesion
from app.dto.emergencias import LiberacionResponseDTO
from app.schemas.emergencias import LiberacionResponse
from app.services.emergencias_service import liberar_emergencia
from app.openapi_examples import ERROR_401, ERROR_422, ERROR_422_PATH, ERROR_503

router = APIRouter(dependencies=[Depends(obtener_cuenta)], tags=["emergencias"], responses={503: {"description": "Configuración o base no disponible", "content": {"application/json": {"example": ERROR_503}}}})


@router.post(
    "/{emergencia_id}/liberar",
    response_model=LiberacionResponse,
    summary="Liberar todos los recursos comprometidos de una emergencia",
    description=(
        "Cambia el estado de todos los compromisos de una emergencia de "
        "`BLOQUEADO` o `COMPROMETIDO` a `LIBERADO`.\n\n"
        "Esto hace que el stock vuelva a estar disponible en "
        "`GET /recursos/disponibilidad`.\n\n"
        "Si la emergencia no tiene compromisos activos, devuelve lista vacía "
        "y total_liberado = 0."
    ),
    responses={
        200: {
            "description": "Recursos liberados",
            "content": {
                "application/json": {
                    "example": {
                        "emergencia_id": 12,
                        "total_liberado": 45,
                        "compromisos_liberados": [
                            {
                                "ong_id": 1,
                                "item_id": 101,
                                "cantidad": 15,
                                "estado_anterior": "COMPROMETIDO",
                                "lote_id": 1,
                            },
                            {
                                "ong_id": 3,
                                "item_id": 101,
                                "cantidad": 25,
                                "estado_anterior": "BLOQUEADO",
                                "lote_id": 1,
                            },
                            {
                                "ong_id": 4,
                                "item_id": 105,
                                "cantidad": 5,
                                "estado_anterior": "COMPROMETIDO",
                                "lote_id": 2,
                            },
                        ],
                    }
                }
            },
        },
        401: {
            "description": "Token ausente o inválido",
            "content": {"application/json": {"example": ERROR_401}},
        },
        422: {"description": "emergencia_id inválido", "content": {"application/json": {"example": ERROR_422_PATH}}},
    },
)
def liberar_emergencia_endpoint(
    emergencia_id: int = Path(..., ge=1, description="ID de la emergencia a liberar"),
    db: Session = Depends(obtener_sesion),
):
    return liberar_emergencia(db, emergencia_id)
