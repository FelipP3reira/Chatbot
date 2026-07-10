"""cria documentos e trechos com embeddings

Revision ID: 7037e312c516
Revises: 37a1c9add2cd
Create Date: 2026-07-10 10:20:56.613066

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "7037e312c516"
down_revision: str | Sequence[str] | None = "37a1c9add2cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documentos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("origem", sa.String(length=500), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "trechos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("documento_id", sa.Uuid(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(384), nullable=False),
        sa.ForeignKeyConstraint(["documento_id"], ["documentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("documento_id", "ordem", name="trecho_unico_por_ordem"),
    )
    op.create_index(op.f("ix_trechos_documento_id"), "trechos", ["documento_id"], unique=False)

    # HNSW para distância do cosseno: a busca é sempre por ORDER BY <=>.
    # Sem o índice, cada pergunta varre a tabela inteira.
    op.execute(
        "CREATE INDEX ix_trechos_embedding ON trechos USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_trechos_embedding", table_name="trechos")
    op.drop_index(op.f("ix_trechos_documento_id"), table_name="trechos")
    op.drop_table("trechos")
    op.drop_table("documentos")
    # A extensão pode estar em uso por outro schema; derrubá-la não é nosso papel.
