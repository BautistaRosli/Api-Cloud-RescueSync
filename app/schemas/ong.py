from typing import Annotated
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.items import ItemRespuesta, OngItemRespuesta


TextoObligatorio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RegistroOng(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cuit: TextoObligatorio
    razon_social: TextoObligatorio
    email: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")]


class OngRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cuit: str
    razon_social: str
    email: str
    items: list[OngItemRespuesta] = []