import pytest

from app.rag.chunker import dividir_em_trechos


def test_texto_curto_vira_um_trecho_so() -> None:
    assert dividir_em_trechos("Uma frase curta.") == ["Uma frase curta."]


def test_texto_vazio_nao_gera_trecho() -> None:
    assert dividir_em_trechos("   \n  ") == []


def test_nenhum_trecho_passa_do_tamanho_pedido() -> None:
    texto = " ".join(f"palavra{i}" for i in range(500))

    trechos = dividir_em_trechos(texto, tamanho=100, sobreposicao=20)

    assert all(len(trecho) <= 100 for trecho in trechos)
    assert len(trechos) > 1


def test_trechos_vizinhos_se_sobrepoem() -> None:
    # A resposta pode estar na emenda; sem sobreposição ela se perde.
    texto = " ".join(f"p{i}" for i in range(200))

    primeiro, segundo = dividir_em_trechos(texto, tamanho=100, sobreposicao=40)[:2]
    fim_do_primeiro = primeiro[-20:]

    assert fim_do_primeiro in segundo


def test_corte_prefere_fim_de_frase() -> None:
    texto = "Primeira frase aqui. " + "x" * 60 + " final"

    primeiro = dividir_em_trechos(texto, tamanho=40, sobreposicao=5)[0]

    assert primeiro == "Primeira frase aqui."


def test_texto_inteiro_sobrevive_a_divisao() -> None:
    texto = " ".join(f"token{i}" for i in range(300))

    trechos = dividir_em_trechos(texto, tamanho=120, sobreposicao=30)

    for palavra in ("token0", "token150", "token299"):
        assert any(palavra in trecho for trecho in trechos)


def test_sobreposicao_maior_que_o_trecho_e_recusada() -> None:
    with pytest.raises(ValueError, match="menor que o tamanho"):
        dividir_em_trechos("texto", tamanho=10, sobreposicao=10)
