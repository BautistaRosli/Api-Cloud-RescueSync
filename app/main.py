from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routes import items, users

app = FastAPI(
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


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
