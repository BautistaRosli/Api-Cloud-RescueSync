from pydantic import BaseModel
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Table, true
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
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

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
    unidad: Mapped[str] = mapped_column(String, default="unidades", server_default="unidades")

    ongs: Mapped[list["Ong"]] = relationship(
        secondary="ong_items",
        back_populates="items"
    )


# Estados que restan stock disponible. LIBERADO ya no cuenta.
ESTADOS_COMPROMETIDOS = ("BLOQUEADO", "COMPROMETIDO")


class CompromisoRecurso(Base):
    """Cantidad de un item de una ONG reservada para una emergencia/lote (la escribe POST /recursos/bloquear)."""
    __tablename__ = "compromisos_recurso"
    __table_args__ = (Index("ix_compromisos_ong_item", "ong_id", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ong_id: Mapped[int] = mapped_column(ForeignKey("ongs.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    emergencia_id: Mapped[int] = mapped_column(Integer)
    lote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cantidad: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String, default="BLOQUEADO")
