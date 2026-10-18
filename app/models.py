from pydantic import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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


class Base(DeclarativeBase):
    pass


class Cuenta(Base):
    __tablename__ = "cuentas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)


class Ong(Base):
    __tablename__ = "ongs"

    id: Mapped[int] = mapped_column(primary_key=True)
    cuit: Mapped[str] = mapped_column(String, unique=True)
    razon_social: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
