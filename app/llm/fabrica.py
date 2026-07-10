from functools import lru_cache

from app.config import obter_configuracao
from app.llm.anthropic_llm import ProvedorAnthropic
from app.llm.base import ProvedorLLM
from app.llm.fake import ProvedorFake
from app.llm.resiliencia import ProvedorResiliente


@lru_cache(maxsize=1)
def obter_provedor() -> ProvedorLLM:
    configuracao = obter_configuracao()

    if configuracao.provedor_llm == "fake":
        return ProvedorResiliente(ProvedorFake())

    # A configuração já garantiu que a chave existe quando o provedor é anthropic.
    assert configuracao.anthropic_api_key is not None
    return ProvedorResiliente(
        ProvedorAnthropic(
            chave=configuracao.anthropic_api_key.get_secret_value(),
            modelo=configuracao.modelo_llm,
        )
    )
