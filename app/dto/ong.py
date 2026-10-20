from pydantic import BaseModel, ConfigDict


class OngCreada(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cuit: str
    razon_social: str
    email: str
