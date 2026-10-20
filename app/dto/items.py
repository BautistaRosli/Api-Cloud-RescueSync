from typing import Optional
from pydantic import BaseModel, ConfigDict


class ItemCreado(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: Optional[str] = None


class OngItemCreado(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ong_id: int
    item_id: int
    cantidad: int

    item: ItemCreado