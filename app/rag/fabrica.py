from functools import lru_cache

from app.config import obter_configuracao
from app.rag.embeddings import Embedder, EmbedderDeHashing, EmbedderLocal


@lru_cache(maxsize=1)
def obter_embedder() -> Embedder:
    configuracao = obter_configuracao()
    if configuracao.embedder == "hashing":
        return EmbedderDeHashing()
    return EmbedderLocal(configuracao.modelo_embedding)
