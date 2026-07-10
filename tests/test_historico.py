from app.conversa.historico import JANELA_DE_MENSAGENS, montar_historico
from app.conversa.modelos import Mensagem, PapelDaMensagem


def _mensagem(ordem: int, papel: PapelDaMensagem) -> Mensagem:
    return Mensagem(ordem=ordem, papel=papel, conteudo=f"m{ordem}")


def _conversa_alternada(quantidade: int) -> list[Mensagem]:
    papeis = [PapelDaMensagem.USUARIO, PapelDaMensagem.ASSISTENTE]
    return [_mensagem(i, papeis[i % 2]) for i in range(quantidade)]


def test_conversa_curta_passa_inteira() -> None:
    historico = montar_historico(_conversa_alternada(4))

    assert [m.conteudo for m in historico] == ["m0", "m1", "m2", "m3"]


def test_janela_corta_as_mensagens_mais_antigas() -> None:
    historico = montar_historico(_conversa_alternada(JANELA_DE_MENSAGENS + 10))

    assert len(historico) <= JANELA_DE_MENSAGENS
    assert historico[-1].conteudo == f"m{JANELA_DE_MENSAGENS + 9}"


def test_historico_sempre_comeca_pelo_usuario() -> None:
    # Um número ímpar de mensagens faz a janela cair sobre uma fala do
    # assistente; ela precisa ser descartada.
    historico = montar_historico(_conversa_alternada(JANELA_DE_MENSAGENS + 1))

    assert historico[0].papel == "usuario"


def test_historico_vazio_nao_quebra() -> None:
    assert montar_historico([]) == []
