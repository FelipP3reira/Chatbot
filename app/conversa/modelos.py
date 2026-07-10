import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PapelDaMensagem(StrEnum):
    USUARIO = "usuario"
    ASSISTENTE = "assistente"


class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tokens_entrada: Mapped[int] = mapped_column(default=0)
    tokens_saida: Mapped[int] = mapped_column(default=0)

    mensagens: Mapped[list["Mensagem"]] = relationship(
        back_populates="conversa",
        cascade="all, delete-orphan",
        order_by="Mensagem.ordem",
    )


class Mensagem(Base):
    __tablename__ = "mensagens"
    # now() no Postgres é o instante em que a transação abriu: a pergunta e a
    # resposta gravadas juntas teriam o mesmo timestamp. A ordem é explícita.
    __table_args__ = (UniqueConstraint("conversa_id", "ordem", name="mensagem_unica_por_ordem"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversas.id", ondelete="CASCADE"), index=True
    )
    ordem: Mapped[int]
    papel: Mapped[PapelDaMensagem]
    conteudo: Mapped[str] = mapped_column(Text)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversa: Mapped[Conversa] = relationship(back_populates="mensagens")
