from fastapi import APIRouter, HTTPException

from app.models import User, UserCreate

router = APIRouter()

fake_db: dict[int, User] = {}
counter = 0


@router.post("/", response_model=User)
def create_user(user: UserCreate):
    global counter
    counter += 1
    new_user = User(id=counter, **user.model_dump())
    fake_db[counter] = new_user
    return new_user


@router.get("/", response_model=list[User])
def list_users():
    return list(fake_db.values())


@router.get("/{user_id}", response_model=User)
def get_user(user_id: int):
    if user_id not in fake_db:
        raise HTTPException(status_code=404, detail="User not found")
    return fake_db[user_id]
