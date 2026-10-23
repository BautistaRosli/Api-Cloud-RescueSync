from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from app.database import iniciar_base_datos
from app.config import cargar_configuracion
from app.routes import auth, emergencias, items, ongs, recursos, users, validaciones
from app.services.bootstrap_service import asegurar_cuenta_rescuesync

@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    app.state.configuracion = cargar_configuracion()
    motor = None
    try:
        if app.state.configuracion is not None:
            motor, app.state.sesiones = iniciar_base_datos(app.state.configuracion.database_url)
            asegurar_cuenta_rescuesync(app.state.sesiones, app.state.configuracion)
        yield
    finally:
        if motor is not None:
            motor.dispose()

app = FastAPI(
    lifespan=ciclo_vida,
    title="Cloud RescueSync API",
    description=(
        "API REST para Cloud RescueSync.\n\n"
        "**Para probar desde Swagger:**\n"
        "1. Ejecutá `POST /auth/login` con el usuario y la contraseña configurados en "
        "`USUARIO_RESCUESYNC` / `PASSWORD_RESCUESYNC`.\n"
        "2. Copiá el `access_token` de la respuesta.\n"
        "3. Hacé clic en **Authorize** y pegá el token.\n"
        "4. Probá `POST /recursos/bloquear` con alguno de los ejemplos del selector **Examples**."
    ),
    version="1.0.0",
    openapi_tags=[
        {
            "name": "autenticación",
            "description": "Login con usuario/contraseña para obtener el JWT que se usa en **Authorize**.",
        },
        {
            "name": "recursos",
            "description": "Inventario de recursos de las ONGs: disponibilidad global y bloqueo.",
        },
        {
            "name": "validaciones",
            "description": "Evaluación de ofertas de ONGs invocada por Bonita (solo lectura).",
        },
        {"name": "ONG", "description": "Registro y consulta de ONGs."},
        {"name": "items", "description": "Catálogo de tipos de recurso e inventario por ONG."},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "docExpansion": "list",
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "operationsSorter": "method",
        "tagsSorter": "alpha",
        "deepLinking": True,
        "filter": True,
        "tryItOutEnabled": True,
        "requestSnippetsEnabled": True,
        "defaultModelsExpandDepth": 1,
        "defaultModelRendering": "example",
    },
)

app.include_router(auth.router, prefix="/auth", tags=["autenticación"])
app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(ongs.router, prefix="/ongs", tags=["ONG"])
app.include_router(recursos.router, prefix="/recursos", tags=["recursos"])
app.include_router(validaciones.router, prefix="/validaciones", tags=["validaciones"])
app.include_router(emergencias.router, prefix="/emergencias", tags=["emergencias"])


@app.exception_handler(RequestValidationError)
async def validacion_sin_credenciales(request: Request, exc: RequestValidationError):
    if request.url.path.rstrip("/") == "/auth/login":
        errores = [
            {"type": error["type"], "loc": error["loc"], "msg": "Credenciales inválidas"}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errores})
    return await request_validation_exception_handler(request, exc)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}