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
# Embeddings sem download: determinísticos e rápidos o bastante para a suíte.
os.environ["EMBEDDER"] = "hashing"
# Banco 1 do Redis: a suite nunca toca no banco 0, usado em desenvolvimento.
os.environ["REDIS_URL"] = "redis://localhost:6383/1"
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://chatbot:chatbot@localhost:5437/{BANCO_DE_TESTES}"
)

from app.config import obter_configuracao  # noqa: E402
from app.limites.redis_cliente import obter_redis  # noqa: E402
from app.llm.fabrica import obter_provedor  # noqa: E402
from app.rag.fabrica import obter_embedder  # noqa: E402


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
    _limpar_caches()
    yield
    _limpar_caches()


def _limpar_caches() -> None:
    obter_configuracao.cache_clear()
    obter_provedor.cache_clear()
    obter_embedder.cache_clear()
    obter_redis.cache_clear()


@pytest.fixture
async def banco_limpo() -> AsyncIterator[None]:
    await obter_redis().flushdb()
    yield

    # O cliente do Redis prende o event loop do teste, que morre com ele.
    await obter_redis().aclose()
    obter_redis.cache_clear()

    # Cada teste roda no seu próprio event loop. O pool do engine guardaria
    # conexões do loop anterior, que morre junto com o teste — daí o descarte.
    from app.db import motor

    await motor.dispose()

    conexao = await asyncpg.connect(f"{SERVIDOR}/{BANCO_DE_TESTES}")
    try:
        await conexao.execute("TRUNCATE conversas, documentos CASCADE")
    finally:
        await conexao.close()
