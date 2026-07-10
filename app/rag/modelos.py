import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.rag.embeddings import DIMENSOES


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    titulo: Mapped[str] = mapped_column(String(300))
    origem: Mapped[str | None] = mapped_column(String(500), default=None)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trechos: Mapped[list["Trecho"]] = relationship(
        back_populates="documento",
        cascade="all, delete-orphan",
        order_by="Trecho.ordem",
    )


class Trecho(Base):
    __tablename__ = "trechos"
    __table_args__ = (UniqueConstraint("documento_id", "ordem", name="trecho_unico_por_ordem"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    documento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documentos.id", ondelete="CASCADE"), index=True
    )
    ordem: Mapped[int]
    conteudo: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(DIMENSOES))

    documento: Mapped[Documento] = relationship(back_populates="trechos")
