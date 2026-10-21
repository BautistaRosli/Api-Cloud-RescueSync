from pydantic import BaseModel
from sqlalchemy import String, Integer, ForeignKey, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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

    items: Mapped[list["Item"]] = relationship(
        secondary="ong_items",
        back_populates="ongs"
    )


# Tabla de asociación para inventario: ONG <-> Item con cantidad
ong_items = Table(
    "ong_items",
    Base.metadata,
    Column("ong_id", Integer, ForeignKey("ongs.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("cantidad", Integer, nullable=False, default=0),
)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String, nullable=True)

    ongs: Mapped[list["Ong"]] = relationship(
        secondary="ong_items",
        back_populates="items"
    )