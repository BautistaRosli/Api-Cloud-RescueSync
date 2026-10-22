from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import obtener_cuenta, obtener_sesion
from app.dto.recursos import DisponibilidadTipo, RespuestaBloqueo
from app.schemas.recursos import SolicitudBloqueo
from app.services.recursos_service import bloquear_recursos, calcular_disponibilidad


router = APIRouter(dependencies=[Depends(obtener_cuenta)])

EJEMPLOS_BLOQUEO = {
    "una_ong": {
        "summary": "Una ONG con un item",
        "value": {
            "emergencia_id": 12,
            "lote_id": 3,
            "ongs": [
                {"ong_id": 1, "items": [{"item_id": 101, "cantidad": 2}]},
            ],
        },
    },
    "varias_ongs": {
        "summary": "Consorcio con varios items (datos del seed)",
        "description": (
            "Cruz Roja (1) bloquea Paramédicos y Médicos Sin Fronteras (3) bloquea "
            "Paramédicos y Agua potable. Se puede ejecutar varias veces."
        ),
        "value": {
            "emergencia_id": 12,
            "lote_id": 3,
            "ongs": [
                {"ong_id": 1, "items": [{"item_id": 101, "cantidad": 2}]},
                {
                    "ong_id": 3,
                    "items": [
                        {"item_id": 101, "cantidad": 3},
                        {"item_id": 104, "cantidad": 10},
                    ],
                },
            ],
        },
    },
}


@router.post(
    "/bloquear",
    response_model=RespuestaBloqueo,
    summary="Bloquear recursos de una o varias ONGs",
    description=(
        "Reserva stock de una o varias ONGs para una emergencia (y opcionalmente un lote). "
        "Escribe una fila por par `(ong_id, item_id)` en `compromisos_recurso` con estado "
        "`BLOQUEADO`; no modifica el inventario de `ong_items`.\n\n"
        "El cálculo del stock disponible y la escritura son atómicos. En PostgreSQL se toman "
        "locks de fila (`SELECT ... FOR UPDATE`) sobre `ongs`, `items` y `ong_items` en orden de "
        "id, de modo que dos requests concurrentes no puedan bloquear más cantidad que la "
        "disponible.\n\n"
        "Si alguna ONG no existe o está inactiva, algún item no existe, la ONG no tiene ese item "
        "asignado o no alcanza el stock, se rechaza el request completo y no se bloquea nada."
    ),
    responses={
        200: {
            "description": "Recursos bloqueados",
            "content": {"application/json": {"example": {
                "emergencia_id": 12,
                "lote_id": 3,
                "total_bloqueado": 15,
                "bloqueados": [
                    {"ong_id": 1, "item_id": 101, "cantidad": 2, "estado": "BLOQUEADO"},
                    {"ong_id": 3, "item_id": 101, "cantidad": 3, "estado": "BLOQUEADO"},
                    {"ong_id": 3, "item_id": 104, "cantidad": 10, "estado": "BLOQUEADO"},
                ],
            }}},
        },
        401: {
            "description": "Token ausente o inválido",
            "content": {"application/json": {"example": {"detail": "Credenciales inválidas"}}},
        },
        404: {
            "description": "ONG o item inexistente",
            "content": {"application/json": {"example": {"detail": "La ONG 999 no existe"}}},
        },
        409: {
            "description": "ONG inactiva, item no asignado o stock insuficiente",
            "content": {"application/json": {"example": {
                "detail": "La ONG 3 no tiene stock suficiente del item 101: solicitado 30, disponible 25",
            }}},
        },
        422: {"description": "Request mal formado"},
    },
)
def bloquear(
    solicitud: SolicitudBloqueo = Body(openapi_examples=EJEMPLOS_BLOQUEO),
    db: Session = Depends(obtener_sesion),
):
    return bloquear_recursos(db, solicitud)


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
