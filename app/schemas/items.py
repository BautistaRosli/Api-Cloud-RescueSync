from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, StringConstraints


TextoObligatorio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TextoOpcional = Annotated[str | None, StringConstraints(strip_whitespace=True)]


class ItemBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: TextoObligatorio
    descripcion: TextoOpcional = None


class ItemCrear(ItemBase):
    pass


class ItemActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: TextoOpcional = None
    descripcion: TextoOpcional = None


class ItemRespuesta(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class OngItemBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: int
    cantidad: int = 0


class OngItemCrear(OngItemBase):
    pass


class OngItemActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cantidad: Optional[int] = None


class OngItemRespuesta(OngItemBase):
    model_config = ConfigDict(from_attributes=True)

    item: ItemRespuesta