from __future__ import annotations
from sqlalchemy import create_engine, ForeignKey, UniqueConstraint, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DATABASE_URL = "sqlite:///./wherearemythings.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # sqlite + threads
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)

    parent = relationship("Location", remote_side=[id])

    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_location_parent_name"),
    )

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class Placement(Base):
    __tablename__ = "placements"
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

def init_db():
    Base.metadata.create_all(bind=engine)
