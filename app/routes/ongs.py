from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.dependencies import obtener_cuenta, obtener_sesion
from app.dto.ong import OngCreada
from app.models import Ong
from app.schemas.ong import RegistroOng, OngRespuesta
from app.schemas.items import OngItemRespuesta
from app.services.ongs_service import registrar_ong
from app.models import ong_items

router = APIRouter(dependencies=[Depends(obtener_cuenta)])


@router.post("/registro", response_model=OngCreada, status_code=201)
def registro(datos: RegistroOng, db: Session = Depends(obtener_sesion)):
    return registrar_ong(db, datos)


@router.get("/{ong_id}", response_model=OngRespuesta)
def obtener_ong(ong_id: int, db: Session = Depends(obtener_sesion)):
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