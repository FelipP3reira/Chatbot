import json
from typing import Any


def ler_eventos(corpo: str) -> list[tuple[str, dict[str, Any]]]:
    """Traduz o corpo `text/event-stream` numa lista de (evento, dados)."""
    eventos = []
    for bloco in corpo.strip().split("\n\n"):
        linha_do_evento, linha_dos_dados = bloco.split("\n")
        nome = linha_do_evento.removeprefix("event: ")
        dados = json.loads(linha_dos_dados.removeprefix("data: "))
        eventos.append((nome, dados))
    return eventos


def texto_recebido(corpo: str) -> str:
    return "".join(dados["texto"] for nome, dados in ler_eventos(corpo) if nome == "pedaco")


def nomes_dos_eventos(corpo: str) -> list[str]:
    return [nome for nome, _ in ler_eventos(corpo)]
