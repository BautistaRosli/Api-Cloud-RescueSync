# Cloud RescueSync API

API REST para Cloud RescueSync construida con FastAPI.

## Iniciar la API (local)

```bash
uvicorn app.main:app --reload
```

La API queda disponible en `http://127.0.0.1:8000`.

## Iniciar con Docker

Levanta la API junto con PostgreSQL:

```bash
docker compose up --build
```

Para detenerlos:

```bash
docker compose down
```

La API queda disponible en `http://localhost:8002`.

> Requiere un archivo `.env` con las variables `DATABASE_URL`, `JWT_SECRET` y `POSTGRES_PASSWORD`. Podés copiar `.env.example` como base.

## Swagger (documentación interactiva)

Una vez iniciada la API, accedé al Swagger en:

- **Local:** http://127.0.0.1:8000/docs
- **Docker:** http://localhost:8002/docs

También está disponible ReDoc en `/redoc`.

## Instalación de dependencias

```bash
pip install -r requirements.txt
```
