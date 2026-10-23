from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


Identificador = Annotated[int, Field(ge=1)]
Cantidad = Annotated[int, Field(ge=1)]


class LoteSolicitado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lote_id: Identificador
    tipo_recurso_id: Identificador
    cantidad_requerida: Cantidad


class ItemOfrecido(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_recurso_id: Identificador
    cantidad: Cantidad


class AporteOng(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ong_id: Identificador
    items: list[ItemOfrecido] = Field(min_length=1)


class OfertaConsolidada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oferta_id: Identificador
    lote_id: Identificador
    ong_responsable_id: Identificador
    aportes: list[AporteOng] = Field(min_length=1)


class SolicitudEvaluacion(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "emergencia_id": 12,
                "lotes": [{"lote_id": 3, "tipo_recurso_id": 1, "cantidad_requerida": 5}],
                "ofertas": [{
                    "oferta_id": 7, "lote_id": 3, "ong_responsable_id": 2,
                    "aportes": [
                        {"ong_id": 2, "items": [{"tipo_recurso_id": 1, "cantidad": 3}]},
                        {"ong_id": 5, "items": [{"tipo_recurso_id": 1, "cantidad": 2}]},
                    ],
                }],
            }
        },
    )

    emergencia_id: Identificador
    lotes: list[LoteSolicitado] = Field(min_length=1)
    ofertas: list[OfertaConsolidada]
