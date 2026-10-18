from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str


class User(UserCreate):
    id: int


class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    owner_id: int


class Item(ItemCreate):
    id: int
