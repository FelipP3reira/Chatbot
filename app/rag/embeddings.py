import asyncio
import hashlib
import math
import re
from collections.abc import Sequence
from typing import Protocol

# Fixado pelo all-MiniLM-L6-v2 e gravado na coluna vector(384) da migração:
# trocar de modelo exige migrar o índice, não só mudar a configuração.
DIMENSOES = 384

_PALAVRA = re.compile(r"\w+", re.UNICODE)


class Embedder(Protocol):
    async def codificar(self, textos: Sequence[str]) -> list[list[float]]: ...


class EmbedderLocal:
    """sentence-transformers rodando na máquina: sem chave, sem rede, sem custo.

    O modelo é carregado na primeira chamada — subir a aplicação não deve
    esperar por centenas de megabytes de peso.
    """

    def __init__(self, nome_do_modelo: str) -> None:
        self._nome_do_modelo = nome_do_modelo
        self._modelo: object | None = None

    async def codificar(self, textos: Sequence[str]) -> list[list[float]]:
        # encode() é CPU-bound e bloquearia o event loop inteiro.
        return await asyncio.to_thread(self._codificar_bloqueando, list(textos))

    def _codificar_bloqueando(self, textos: list[str]) -> list[list[float]]:
        from sentence_transformers import SentenceTransformer

        if self._modelo is None:
            self._modelo = SentenceTransformer(self._nome_do_modelo)

        assert isinstance(self._modelo, SentenceTransformer)
        vetores = self._modelo.encode(textos, normalize_embeddings=True)
        return [[float(valor) for valor in vetor] for vetor in vetores]


class EmbedderDeHashing:
    """Saco de palavras projetado por hash, sem dependência nem download.

    Não entende sinônimos — mas é determinístico entre processos e captura
    sobreposição de vocabulário, que é o suficiente para os testes do pipeline
    e para rodar o projeto numa máquina sem espaço para o modelo.
    """

    async def codificar(self, textos: Sequence[str]) -> list[list[float]]:
        return [self._vetor(texto) for texto in textos]

    def _vetor(self, texto: str) -> list[float]:
        vetor = [0.0] * DIMENSOES
        for palavra in _PALAVRA.findall(texto.lower()):
            vetor[_balde(palavra)] += 1.0
        return _normalizar(vetor)


def _balde(palavra: str) -> int:
    # hash() do Python muda a cada processo; o índice no banco não pode mudar.
    digest = hashlib.blake2b(palavra.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % DIMENSOES


def _normalizar(vetor: list[float]) -> list[float]:
    norma = math.sqrt(sum(valor * valor for valor in vetor))
    if norma == 0:
        return vetor
    return [valor / norma for valor in vetor]
