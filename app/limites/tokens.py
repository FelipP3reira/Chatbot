CARACTERES_POR_TOKEN = 4


def estimar_tokens(texto: str) -> int:
    """Estimativa grosseira, não a contagem do provedor.

    Serve para barrar uma sessão que está gastando demais antes de a conta
    chegar; a cobrança real vem do provedor. Erra para mais em português, o que
    é o lado seguro de errar.
    """
    return len(texto) // CARACTERES_POR_TOKEN + 1
