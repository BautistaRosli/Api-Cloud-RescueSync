from fastapi import APIRouter, Body, HTTPException, Path

from app.models import User, UserCreate
from app.openapi_examples import ERROR_422, ERROR_422_PATH

router = APIRouter()

fake_db: dict[int, User] = {}
counter = 0


@router.post(
    "/", response_model=User,
    responses={
        200: {"description": "Usuario creado", "content": {"application/json": {"example": {"id": 1, "name": "Ana", "email": "ana@example.org"}}}},
        422: {"description": "Datos inválidos", "content": {"application/json": {"example": ERROR_422}}},
    },
)
def create_user(user: UserCreate = Body(example={"name": "Ana", "email": "ana@example.org"})):
    global counter
    counter += 1
    new_user = User(id=counter, **user.model_dump())
    fake_db[counter] = new_user
    return new_user


@router.get(
    "/", response_model=list[User],
    responses={200: {"description": "Usuarios encontrados", "content": {"application/json": {"example": []}}}},
)
def list_users():
    return list(fake_db.values())


@router.get(
    "/{user_id}", response_model=User,
    responses={
        200: {"description": "Usuario encontrado", "content": {"application/json": {"example": {"id": 1, "name": "Ana", "email": "ana@example.org"}}}},
        404: {"description": "Usuario inexistente", "content": {"application/json": {"example": {"detail": "User not found"}}}},
        422: {"description": "ID inválido", "content": {"application/json": {"example": ERROR_422_PATH}}},
    },
)
def get_user(user_id: int = Path(..., ge=1, example=1)):
    if user_id not in fake_db:
        raise HTTPException(status_code=404, detail="User not found")
    return fake_db[user_id]
