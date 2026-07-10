TAMANHO_DO_TRECHO = 800
SOBREPOSICAO = 150


def dividir_em_trechos(
    texto: str,
    tamanho: int = TAMANHO_DO_TRECHO,
    sobreposicao: int = SOBREPOSICAO,
) -> list[str]:
    """Corta o texto em trechos com sobreposição.

    A sobreposição existe porque a resposta pode estar bem na emenda: sem ela,
    uma frase partida ao meio não é recuperada por nenhum dos dois lados.
    """
    if sobreposicao >= tamanho:
        raise ValueError("A sobreposição precisa ser menor que o tamanho do trecho.")

    limpo = texto.strip()
    if not limpo:
        return []

    trechos: list[str] = []
    inicio = 0
    while inicio < len(limpo):
        fim = min(inicio + tamanho, len(limpo))
        corte = _recuar_ate_fronteira(limpo, inicio, fim)
        trechos.append(limpo[inicio:corte].strip())

        if corte >= len(limpo):
            break
        inicio = max(corte - sobreposicao, inicio + 1)

    return [trecho for trecho in trechos if trecho]


def _recuar_ate_fronteira(texto: str, inicio: int, fim: int) -> int:
    """Prefere cortar num fim de frase ou espaço a partir uma palavra ao meio."""
    if fim >= len(texto):
        return len(texto)

    minimo_aceitavel = inicio + (fim - inicio) // 2
    for separadores in (". ", "\n"), (" ",):
        for separador in separadores:
            posicao = texto.rfind(separador, minimo_aceitavel, fim)
            if posicao != -1:
                return posicao + len(separador)

    return fim
