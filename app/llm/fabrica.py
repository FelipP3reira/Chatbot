from functools import lru_cache

from app.config import obter_configuracao
from app.llm.anthropic_llm import ProvedorAnthropic
from app.llm.base import ProvedorLLM
from app.llm.fake import ProvedorFake


@lru_cache(maxsize=1)
def obter_provedor() -> ProvedorLLM:
    configuracao = obter_configuracao()
    if configuracao.provedor_llm == "fake":
        return ProvedorFake()

    # A configuração já garantiu que a chave existe quando o provedor é anthropic.
    assert configuracao.anthropic_api_key is not None
    return ProvedorAnthropic(
        chave=configuracao.anthropic_api_key.get_secret_value(),
        modelo=configuracao.modelo_llm,
    )
