from pydantic import BaseModel, ConfigDict


class DisponibilidadTipo(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "tipo_recurso_id": 1, "nombre": "Paramédicos", "unidad": "personas",
                "total": 120, "comprometido": 40, "disponible": 80,
            }
        },
    )

    tipo_recurso_id: int
    nombre: str
    unidad: str
    total: int
    comprometido: int
    disponible: int
