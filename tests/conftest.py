import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator

import asyncpg
import pytest

# Definido antes de qualquer import de app.config: a configuração é lida uma vez
# só, e a suíte nunca deve encostar no banco de desenvolvimento.
BANCO_DE_TESTES = "chatbot_teste"
SERVIDOR = "postgresql://chatbot:chatbot@localhost:5437"

os.environ["AMBIENTE"] = "teste"
os.environ["PROVEDOR_LLM"] = "fake"
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://chatbot:chatbot@localhost:5437/{BANCO_DE_TESTES}"
)

from app.config import obter_configuracao  # noqa: E402
from app.llm.fabrica import obter_provedor  # noqa: E402


async def _criar_banco_se_faltar() -> None:
    conexao = await asyncpg.connect(f"{SERVIDOR}/postgres")
    try:
        existe = await conexao.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", BANCO_DE_TESTES
        )
        if not existe:
            await conexao.execute(f'CREATE DATABASE "{BANCO_DE_TESTES}"')
    finally:
        await conexao.close()


@pytest.fixture(scope="session", autouse=True)
def _banco_migrado() -> None:
    asyncio.run(_criar_banco_se_faltar())
    # Roda a migração de verdade, não um create_all paralelo: assim a suíte
    # falha se a migração divergir dos modelos.
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


@pytest.fixture(autouse=True)
def _caches_limpos() -> Iterator[None]:
    obter_configuracao.cache_clear()
    obter_provedor.cache_clear()
    yield
    obter_configuracao.cache_clear()
    obter_provedor.cache_clear()


@pytest.fixture
async def banco_limpo() -> AsyncIterator[None]:
    yield

    # Cada teste roda no seu próprio event loop. O pool do engine guardaria
    # conexões do loop anterior, que morre junto com o teste — daí o descarte.
    from app.db import motor

    await motor.dispose()

    conexao = await asyncpg.connect(f"{SERVIDOR}/{BANCO_DE_TESTES}")
    try:
        await conexao.execute("TRUNCATE conversas CASCADE")
    finally:
        await conexao.close()
