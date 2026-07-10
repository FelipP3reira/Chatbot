import asyncio
from collections.abc import AsyncIterator, Sequence

import pytest

from app.llm.base import ErroTemporarioDoProvedor, MensagemDoModelo, ProvedorIndisponivel
from app.llm.resiliencia import ProvedorResiliente

PERGUNTA = [MensagemDoModelo(papel="usuario", conteudo="oi")]
_NADA: list[str] = []


class ProvedorInstavel:
    """Falha nas primeiras `falhas` chamadas e depois responde."""

    def __init__(self, falhas: int) -> None:
        self.falhas_restantes = falhas
        self.chamadas = 0

    async def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        self.chamadas += 1
        if self.falhas_restantes > 0:
            self.falhas_restantes -= 1
            raise ErroTemporarioDoProvedor("caiu")
        yield "tudo certo"


class ProvedorQueFalhaNoMeio:
    def __init__(self) -> None:
        self.chamadas = 0

    async def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        self.chamadas += 1
        yield "comecei"
        raise ErroTemporarioDoProvedor("caiu no meio")


class ProvedorMudo:
    async def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        await asyncio.sleep(10)
        yield "tarde demais"


class ProvedorComErroPermanente:
    def __init__(self) -> None:
        self.chamadas = 0

    async def gerar_stream(
        self, sistema: str, mensagens: Sequence[MensagemDoModelo]
    ) -> AsyncIterator[str]:
        self.chamadas += 1
        for pedaco in _NADA:  # falha sem chegar a emitir pedaço nenhum
            yield pedaco
        raise ProvedorIndisponivel("pedido inválido")


def _resiliente(provedor: object, **ajustes: object) -> ProvedorResiliente:
    padrao: dict[str, object] = {"tentativas": 3, "espera_base_ms": 1}
    return ProvedorResiliente(provedor, **{**padrao, **ajustes})  # type: ignore[arg-type]


async def _coletar(provedor: ProvedorResiliente) -> str:
    return "".join([pedaco async for pedaco in provedor.gerar_stream("sistema", PERGUNTA)])


async def test_falha_temporaria_e_repetida_ate_dar_certo() -> None:
    instavel = ProvedorInstavel(falhas=2)

    assert await _coletar(_resiliente(instavel)) == "tudo certo"
    assert instavel.chamadas == 3


async def test_desiste_depois_das_tentativas() -> None:
    instavel = ProvedorInstavel(falhas=99)

    with pytest.raises(ProvedorIndisponivel):
        await _coletar(_resiliente(instavel))

    assert instavel.chamadas == 3


async def test_nao_repete_depois_de_ja_ter_enviado_texto() -> None:
    # Repetir duplicaria na tela o que o usuário já leu.
    provedor = ProvedorQueFalhaNoMeio()

    with pytest.raises(ProvedorIndisponivel):
        await _coletar(_resiliente(provedor))

    assert provedor.chamadas == 1


async def test_provedor_mudo_estoura_o_limite_de_espera() -> None:
    resiliente = _resiliente(ProvedorMudo(), tentativas=1, segundos_sem_pedaco=0.05)

    with pytest.raises(ProvedorIndisponivel):
        await _coletar(resiliente)


async def test_erro_permanente_nao_gasta_tentativas() -> None:
    provedor = ProvedorComErroPermanente()

    with pytest.raises(ProvedorIndisponivel):
        await _coletar(_resiliente(provedor))

    assert provedor.chamadas == 1
