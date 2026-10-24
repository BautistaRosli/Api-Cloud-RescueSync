"""Ejemplos reutilizables para que todos los endpoints sean ejecutables desde Swagger."""

ERROR_401 = {"detail": "Credenciales inválidas"}
ERROR_503 = {"detail": "Configurar DATABASE_URL y JWT_SECRET para usar este servicio"}
ERROR_422 = {
    "detail": [{"type": "missing", "loc": ["body", "campo"], "msg": "Field required"}]
}
ERROR_422_PATH = {
    "detail": [{"type": "greater_than_equal", "loc": ["path", "id"], "msg": "Input should be greater than or equal to 1"}]
}
ERROR_422_QUERY = {
    "detail": [{"type": "greater_than_equal", "loc": ["query", "tipo_recurso_id"], "msg": "Input should be greater than or equal to 1"}]
}
ITEM = {"id": 101, "nombre": "Paramédicos", "descripcion": "Personal de atención médica"}
ONG = {
    "id": 1,
    "cuit": "30712345678",
    "razon_social": "Cruz Roja Argentina",
    "email": "contacto@cruzroja.org.ar",
}


def error_404(detail: str):
    return {"detail": detail}


def error_409(detail: str):
    return {"detail": detail}
