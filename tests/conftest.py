import os
from collections.abc import Iterator

import pytest

# Definido antes de qualquer import de app.config: a configuração é lida uma vez só.
os.environ["AMBIENTE"] = "teste"
os.environ["PROVEDOR_LLM"] = "fake"

from app.config import obter_configuracao


@pytest.fixture(autouse=True)
def _configuracao_limpa() -> Iterator[None]:
    obter_configuracao.cache_clear()
    yield
    obter_configuracao.cache_clear()
