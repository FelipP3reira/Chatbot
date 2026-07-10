import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import obter_configuracao

# Importado pelo efeito colateral: registra as tabelas em Base.metadata.
from app.conversa import modelos as modelos_de_conversa  # noqa: F401
from app.db import Base
from app.rag import modelos as modelos_de_rag  # noqa: F401

configuracao_alembic = context.config
# A URL vem do ambiente, não do alembic.ini: um lugar só para configurar.
configuracao_alembic.set_main_option("sqlalchemy.url", obter_configuracao().database_url)

if configuracao_alembic.config_file_name is not None:
    fileConfig(configuracao_alembic.config_file_name)

target_metadata = Base.metadata


def executar_offline() -> None:
    context.configure(
        url=configuracao_alembic.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _migrar(conexao: Connection) -> None:
    context.configure(connection=conexao, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def executar_online() -> None:
    motor = async_engine_from_config(
        configuracao_alembic.get_section(configuracao_alembic.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with motor.connect() as conexao:
        await conexao.run_sync(_migrar)
    await motor.dispose()


if context.is_offline_mode():
    executar_offline()
else:
    asyncio.run(executar_online())
