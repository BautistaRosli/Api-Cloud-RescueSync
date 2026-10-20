from pydantic import BaseModel, ConfigDict


class CuentaCreada(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario: str


class TokenAcceso(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
