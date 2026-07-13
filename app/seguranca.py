from collections.abc import Awaitable, Callable

from fastapi import Request, Response

# Sem 'unsafe-inline': todo script e todo estilo vêm de arquivo próprio. Se um
# dia uma resposta do modelo escapar da sanitização e virar <script> na página,
# o navegador se recusa a executá-lo.
_POLITICA_DE_CONTEUDO = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "connect-src 'self'",
        "img-src 'self'",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
    ]
)

CABECALHOS = {
    "Content-Security-Policy": _POLITICA_DE_CONTEUDO,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}


async def aplicar_cabecalhos_de_seguranca(
    requisicao: Request, chamar_proximo: Callable[[Request], Awaitable[Response]]
) -> Response:
    resposta = await chamar_proximo(requisicao)
    for nome, valor in CABECALHOS.items():
        resposta.headers.setdefault(nome, valor)
    return resposta
