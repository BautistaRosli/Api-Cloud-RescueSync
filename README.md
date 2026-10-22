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

## Cambios de esquema sin migraciones

Las tablas se crean con `Base.metadata.create_all` al iniciar, que **no agrega columnas a tablas existentes**.
Si tu base ya tenía datos antes de agregar `ongs.activa`, `items.unidad` y la tabla `compromisos_recurso`,
recreá el volumen (`docker compose down -v && docker compose up --build`) o aplicá a mano:

```sql
ALTER TABLE ongs ADD COLUMN activa BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE items ADD COLUMN unidad VARCHAR NOT NULL DEFAULT 'unidades';
```

## Recursos y validación de ofertas

- `GET /recursos/disponibilidad`: total, comprometido (BLOQUEADO/COMPROMETIDO) y disponible por tipo de recurso
  (`items`), solo de ONGs activas. Filtros opcionales `tipo_recurso_id` y `ong_id`.
- `POST /recursos/bloquear`: reserva stock de una o varias ONGs para una emergencia/lote. Escribe en
  `compromisos_recurso` con estado `BLOQUEADO` (no modifica `ong_items`). El request se rechaza completo si alguna
  ONG no existe/está inactiva, el item no existe o no está asignado, o no alcanza el stock. En PostgreSQL usa
  `SELECT ... FOR UPDATE` sobre `ongs`, `items` y `ong_items`, en orden de id, para que dos requests concurrentes
  no bloqueen de más.

  ```json
  {
    "emergencia_id": 12,
    "lote_id": 3,
    "ongs": [
      {"ong_id": 1, "items": [{"item_id": 101, "cantidad": 20}]},
      {"ong_id": 3, "items": [{"item_id": 101, "cantidad": 2}, {"item_id": 105, "cantidad": 1}]}
    ]
  }
  ```

- `POST /validaciones/evaluar-ofertas`: lo llama Bonita con las ofertas consolidadas; devuelve un perfil por oferta
  (nivel de habilitación, cobertura, roles PRINCIPAL/APOYO_SECUNDARIO y observaciones). No guarda ni bloquea nada.
- El seed agrega los tipos Paramédicos, Bomberos, Raciones de alimento, Agua potable, Camiones y Frazadas
  (ids 101 a 106), una ONG inactiva (id 6) y algunos compromisos para probar desde `/docs`.
