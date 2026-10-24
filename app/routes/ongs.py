from fastapi import APIRouter, Body, Depends, Path
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.dependencies import obtener_cuenta, obtener_sesion
from app.dto.ong import OngCreada
from app.models import Ong
from app.schemas.ong import RegistroOng, OngRespuesta
from app.schemas.items import OngItemRespuesta
from app.services.ongs_service import registrar_ong
from app.models import ong_items
from app.openapi_examples import ERROR_401, ERROR_422, ERROR_422_PATH, ERROR_503, ONG, error_404, error_409

router = APIRouter(dependencies=[Depends(obtener_cuenta)], responses={503: {"description": "Configuración o base no disponible", "content": {"application/json": {"example": ERROR_503}}}})


@router.post(
    "/registro", response_model=OngCreada, status_code=201,
    responses={
        201: {"description": "ONG registrada", "content": {"application/json": {"example": ONG}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        409: {"description": "CUIT duplicado", "content": {"application/json": {"example": error_409("El CUIT ya está registrado")}}},
        422: {"description": "Datos inválidos", "content": {"application/json": {"example": ERROR_422}}},
    },
)
def registro(datos: RegistroOng = Body(example={"cuit": "30712345678", "razon_social": "Cruz Roja Argentina", "email": "contacto@cruzroja.org.ar"}), db: Session = Depends(obtener_sesion)):
    return registrar_ong(db, datos)


@router.get(
    "/{ong_id}", response_model=OngRespuesta,
    responses={
        200: {"description": "ONG encontrada", "content": {"application/json": {"example": {**ONG, "items": [{"item_id": 101, "cantidad": 25, "item": {"id": 101, "nombre": "Paramédicos", "descripcion": "Personal de atención médica"}}]}}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        404: {"description": "ONG inexistente", "content": {"application/json": {"example": error_404("ONG no encontrada")}}},
        422: {"description": "ID inválido", "content": {"application/json": {"example": ERROR_422_PATH}}},
    },
)
def obtener_ong(ong_id: int = Path(..., ge=1, example=1), db: Session = Depends(obtener_sesion)):
    ong = db.execute(
        select(Ong)
        .options(selectinload(Ong.items))
        .where(Ong.id == ong_id)
    ).scalar_one_or_none()

    if not ong:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="ONG no encontrada")

    # Obtener cantidades de la tabla de asociación
    cantidades = db.execute(
        select(ong_items).where(ong_items.c.ong_id == ong_id)
    ).all()

    cantidades_map = {row.item_id: row.cantidad for row in cantidades}

    items_con_cantidad = [
        OngItemRespuesta(
            item_id=item.id,
            cantidad=cantidades_map.get(item.id, 0),
            item=item
        )
        for item in ong.items
    ]

    return OngRespuesta(
        id=ong.id,
        cuit=ong.cuit,
        razon_social=ong.razon_social,
        email=ong.email,
        items=items_con_cantidad
    )
