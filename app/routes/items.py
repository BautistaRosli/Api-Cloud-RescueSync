from fastapi import APIRouter, Body, Depends, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import obtener_cuenta, obtener_sesion
from app.dto.items import ItemCreado, OngItemCreado
from app.schemas.items import ItemCrear, ItemActualizar, OngItemCrear, OngItemActualizar, OngItemRespuesta
from app.services.items_service import (
    crear_item,
    listar_items,
    obtener_item,
    actualizar_item,
    eliminar_item,
    agregar_item_a_ong,
    actualizar_cantidad_item_ong,
    eliminar_item_de_ong,
    obtener_ong_con_items,
)
from app.openapi_examples import ERROR_401, ERROR_422, ERROR_422_PATH, ERROR_503, ITEM, error_404, error_409

router = APIRouter(dependencies=[Depends(obtener_cuenta)], responses={503: {"description": "Configuración o base no disponible", "content": {"application/json": {"example": ERROR_503}}}})


# Rutas de items (CRUD básico)
@router.post(
    "", response_model=ItemCreado, status_code=201,
    responses={
        201: {"description": "Item creado", "content": {"application/json": {"example": ITEM}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        409: {"description": "No se pudo crear el item", "content": {"application/json": {"example": error_409("Error al crear el item")}}},
        422: {"description": "Datos inválidos", "content": {"application/json": {"example": ERROR_422}}},
    },
)
def crear_item_endpoint(datos: ItemCrear = Body(example={"nombre": "Paramédicos", "descripcion": "Personal de atención médica"}), db: Session = Depends(obtener_sesion)):
    return crear_item(db, datos)


@router.get(
    "", response_model=list[ItemCreado],
    responses={200: {"description": "Items encontrados", "content": {"application/json": {"example": [ITEM]}}}, 401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}}},
)
def listar_items_endpoint(db: Session = Depends(obtener_sesion)):
    return listar_items(db)


@router.get(
    "/{item_id}", response_model=ItemCreado,
    responses={
        200: {"description": "Item encontrado", "content": {"application/json": {"example": ITEM}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        404: {"description": "Item inexistente", "content": {"application/json": {"example": error_404("Item no encontrado")}}},
        422: {"description": "ID inválido", "content": {"application/json": {"example": ERROR_422_PATH}}},
    },
)
def obtener_item_endpoint(item_id: int = Path(..., ge=1, example=101), db: Session = Depends(obtener_sesion)):
    return obtener_item(db, item_id)


@router.patch(
    "/{item_id}", response_model=ItemCreado,
    responses={
        200: {"description": "Item actualizado", "content": {"application/json": {"example": ITEM}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        404: {"description": "Item inexistente", "content": {"application/json": {"example": error_404("Item no encontrado")}}},
        409: {"description": "No se pudo actualizar el item", "content": {"application/json": {"example": error_409("Error al actualizar el item")}}},
        422: {"description": "Datos inválidos", "content": {"application/json": {"example": ERROR_422}}},
    },
)
def actualizar_item_endpoint(item_id: int = Path(..., ge=1, example=101), datos: ItemActualizar = Body(example={"descripcion": "Paramédicos disponibles"}), db: Session = Depends(obtener_sesion)):
    return actualizar_item(db, item_id, datos)


@router.delete(
    "/{item_id}", status_code=204,
    responses={
        204: {"description": "Item eliminado; la respuesta no tiene cuerpo"},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        404: {"description": "Item inexistente", "content": {"application/json": {"example": error_404("Item no encontrado")}}},
        422: {"description": "ID inválido", "content": {"application/json": {"example": ERROR_422_PATH}}},
    },
)
def eliminar_item_endpoint(item_id: int = Path(..., ge=1, example=101), db: Session = Depends(obtener_sesion)):
    return eliminar_item(db, item_id)


# Rutas de inventario por ONG
@router.post(
    "/ongs/{ong_id}/items", response_model=OngItemCreado, status_code=201,
    responses={
        201: {"description": "Item agregado al inventario", "content": {"application/json": {"example": {"ong_id": 1, "item_id": 101, "cantidad": 25, "item": ITEM}}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        404: {"description": "ONG o item inexistente", "content": {"application/json": {"example": error_404("ONG no encontrada")}}},
        409: {"description": "Item ya asignado", "content": {"application/json": {"example": error_409("El item ya está en el inventario de esta ONG")}}},
        422: {"description": "Datos inválidos", "content": {"application/json": {"example": ERROR_422}}},
    },
)
def agregar_item_a_ong_endpoint(ong_id: int = Path(..., ge=1, example=1), datos: OngItemCrear = Body(example={"item_id": 101, "cantidad": 25}), db: Session = Depends(obtener_sesion)):
    return agregar_item_a_ong(db, ong_id, datos)


@router.patch(
    "/ongs/{ong_id}/items/{item_id}", response_model=OngItemCreado,
    responses={
        200: {"description": "Cantidad actualizada", "content": {"application/json": {"example": {"ong_id": 1, "item_id": 101, "cantidad": 30, "item": ITEM}}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        404: {"description": "ONG, item o relación inexistente", "content": {"application/json": {"example": error_404("El item no está en el inventario de esta ONG")}}},
        422: {"description": "Datos inválidos", "content": {"application/json": {"example": ERROR_422}}},
    },
)
def actualizar_cantidad_item_ong_endpoint(
    ong_id: int = Path(..., ge=1, example=1),
    item_id: int = Path(..., ge=1, example=101),
    datos: OngItemActualizar = Body(example={"cantidad": 30}),
    db: Session = Depends(obtener_sesion)
):
    return actualizar_cantidad_item_ong(db, ong_id, item_id, datos)


@router.delete(
    "/ongs/{ong_id}/items/{item_id}", status_code=204,
    responses={
        204: {"description": "Item quitado del inventario; la respuesta no tiene cuerpo"},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        404: {"description": "ONG o relación inexistente", "content": {"application/json": {"example": error_404("El item no está en el inventario de esta ONG")}}},
        422: {"description": "IDs inválidos", "content": {"application/json": {"example": ERROR_422_PATH}}},
    },
)
def eliminar_item_de_ong_endpoint(ong_id: int = Path(..., ge=1, example=1), item_id: int = Path(..., ge=1, example=101), db: Session = Depends(obtener_sesion)):
    return eliminar_item_de_ong(db, ong_id, item_id)


@router.get(
    "/ongs/{ong_id}", response_model=list[OngItemRespuesta],
    responses={
        200: {"description": "Inventario encontrado", "content": {"application/json": {"example": [{"item_id": 101, "cantidad": 25, "item": ITEM}]}}},
        401: {"description": "Token ausente o inválido", "content": {"application/json": {"example": ERROR_401}}},
        404: {"description": "ONG inexistente", "content": {"application/json": {"example": error_404("ONG no encontrada")}}},
        422: {"description": "ID inválido", "content": {"application/json": {"example": ERROR_422_PATH}}},
    },
)
def obtener_inventario_ong(ong_id: int = Path(..., ge=1, example=1), db: Session = Depends(obtener_sesion)):
    ong = obtener_ong_con_items(db, ong_id)

    # Obtener cantidades de la tabla de asociación
    from app.models import ong_items
    cantidades = db.execute(
        select(ong_items).where(ong_items.c.ong_id == ong_id)
    ).all()

    cantidades_map = {row.item_id: row.cantidad for row in cantidades}

    resultado = []
    for item in ong.items:
        resultado.append(OngItemRespuesta(
            item_id=item.id,
            cantidad=cantidades_map.get(item.id, 0),
            item=item
        ))

    return resultado
