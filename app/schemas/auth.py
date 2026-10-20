from typing import Annotated

from pydantic import BaseModel, ConfigDict, SecretStr, StringConstraints, field_validator


class Credenciales(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    password: SecretStr

    @field_validator("password")
    @classmethod
    def validar_password(cls, valor: SecretStr) -> SecretStr:
        if not valor.get_secret_value().strip():
            raise ValueError("La contraseña es obligatoria")
        return valor
