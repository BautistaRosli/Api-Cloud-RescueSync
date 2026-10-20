from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from app.database import iniciar_base_datos
from app.config import cargar_configuracion
from app.routes import auth, items, ongs, recursos, users, validaciones


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    app.state.configuracion = cargar_configuracion()
    motor = None
    if app.state.configuracion is not None:
        motor, app.state.sesiones = iniciar_base_datos(app.state.configuracion.database_url)
    try:
        yield
    finally:
        if motor is not None:
            motor.dispose()

app = FastAPI(
    lifespan=ciclo_vida,
    title="Cloud RescueSync API",
    description="API REST para Cloud RescueSync",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "docExpansion": "none",
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "operationsSorter": "method",
        "tagsSorter": "alpha",
        "deepLinking": True,
        "filter": True,
    },
)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(auth.router, prefix="/auth", tags=["autenticación"])
app.include_router(ongs.router, prefix="/ongs", tags=["ONG"])
app.include_router(recursos.router, prefix="/recursos", tags=["recursos"])
app.include_router(validaciones.router, prefix="/validaciones", tags=["validaciones"])


@app.exception_handler(RequestValidationError)
async def validacion_sin_credenciales(request: Request, exc: RequestValidationError):
    if request.url.path.rstrip("/") in {"/auth/registro", "/auth/login"}:
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
