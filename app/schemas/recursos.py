from typing import Annotated

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


Identificador = Annotated[int, Field(ge=1)]
Cantidad = Annotated[int, Field(ge=1)]


class ItemABloquear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # En el resto de la API el catálogo de recursos se llama `items`, pero la
    # validación de ofertas usa `tipo_recurso_id` para el mismo id.
    item_id: Identificador = Field(
        validation_alias=AliasChoices("item_id", "tipo_recurso_id", "recurso_id")
    )
    cantidad: Cantidad


class OngABloquear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ong_id: Identificador
    items: list[ItemABloquear] = Field(min_length=1)


class SolicitudBloqueo(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "emergencia_id": 12,
                "lote_id": 3,
                "ongs": [
                    {"ong_id": 1, "items": [{"item_id": 101, "cantidad": 20}]},
                    {
                        "ong_id": 3,
                        "items": [
                            {"item_id": 101, "cantidad": 2},
                            {"item_id": 105, "cantidad": 1},
                        ],
                    },
                ],
            }
        },
    )

    emergencia_id: Identificador
    lote_id: Identificador | None = None
    ongs: list[OngABloquear] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def aceptar_asignaciones_planas(cls, datos):
        """Acepta también una lista plana de asignaciones, sin cambiar el contrato principal.

        Formato principal (agrupado por ONG):
            {"ongs": [{"ong_id": 1, "items": [{"item_id": 101, "cantidad": 2}]}]}

        Alias aceptados:
            {"asignaciones": [{"ong_id": 1, "item_id": 101, "cantidad": 2}]}
            {"items": [{"ong_id": 1, "tipo_recurso_id": 101, "cantidad": 2}]}
        """
        if not isinstance(datos, dict) or "ongs" in datos:
            return datos

        datos = dict(datos)
        planas = None
        for clave in ("asignaciones", "items", "recursos", "bloqueos"):
            if clave in datos:
                planas = datos.pop(clave)
                break
        if not isinstance(planas, list):
            return datos

        # Variante agrupada con otra clave en la raíz.
        if all(isinstance(fila, dict) and "ong_id" in fila and "items" in fila for fila in planas):
            datos["ongs"] = [{"ong_id": fila["ong_id"], "items": fila["items"]} for fila in planas]
            return datos

        agrupadas: dict[int, list[dict]] = {}
        for asignacion in planas:
            if not isinstance(asignacion, dict):
                return datos
            ong_id = asignacion.get("ong_id")
            item_id = asignacion.get(
                "item_id", asignacion.get("tipo_recurso_id", asignacion.get("recurso_id"))
            )
            cantidad = asignacion.get("cantidad")
            if ong_id is None or item_id is None or cantidad is None:
                return datos
            try:
                hash(ong_id)
            except TypeError:
                return datos
            agrupadas.setdefault(ong_id, []).append({"item_id": item_id, "cantidad": cantidad})

        datos["ongs"] = [{"ong_id": ong_id, "items": items} for ong_id, items in agrupadas.items()]
        return datos
