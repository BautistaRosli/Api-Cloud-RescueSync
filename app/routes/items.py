from fastapi import APIRouter, Depends
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

router = APIRouter(dependencies=[Depends(obtener_cuenta)])


# Rutas de items (CRUD básico)
@router.post("", response_model=ItemCreado, status_code=201)
def crear_item_endpoint(datos: ItemCrear, db: Session = Depends(obtener_sesion)):
    return crear_item(db, datos)


@router.get("", response_model=list[ItemCreado])
def listar_items_endpoint(db: Session = Depends(obtener_sesion)):
    return listar_items(db)


@router.get("/{item_id}", response_model=ItemCreado)
def obtener_item_endpoint(item_id: int, db: Session = Depends(obtener_sesion)):
    return obtener_item(db, item_id)


@router.patch("/{item_id}", response_model=ItemCreado)
def actualizar_item_endpoint(item_id: int, datos: ItemActualizar, db: Session = Depends(obtener_sesion)):
    return actualizar_item(db, item_id, datos)


@router.delete("/{item_id}", status_code=204)
def eliminar_item_endpoint(item_id: int, db: Session = Depends(obtener_sesion)):
    return eliminar_item(db, item_id)


# Rutas de inventario por ONG
@router.post("/ongs/{ong_id}/items", response_model=OngItemCreado, status_code=201)
def agregar_item_a_ong_endpoint(ong_id: int, datos: OngItemCrear, db: Session = Depends(obtener_sesion)):
    return agregar_item_a_ong(db, ong_id, datos)


@router.patch("/ongs/{ong_id}/items/{item_id}", response_model=OngItemCreado)
def actualizar_cantidad_item_ong_endpoint(
    ong_id: int,
    item_id: int,
    datos: OngItemActualizar,
    db: Session = Depends(obtener_sesion)
):
    return actualizar_cantidad_item_ong(db, ong_id, item_id, datos)


@router.delete("/ongs/{ong_id}/items/{item_id}", status_code=204)
def eliminar_item_de_ong_endpoint(ong_id: int, item_id: int, db: Session = Depends(obtener_sesion)):
    return eliminar_item_de_ong(db, ong_id, item_id)


@router.get("/ongs/{ong_id}", response_model=list[OngItemRespuesta])
def obtener_inventario_ong(ong_id: int, db: Session = Depends(obtener_sesion)):
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
