from collections.abc import Sequence

from app.conversa.modelos import Mensagem, PapelDaMensagem
from app.llm.base import MensagemDoModelo

# Quantas mensagens do passado seguem no prompt. Cortar pelo fim mantém o
# assunto atual; a conversa inteira continua no banco.
JANELA_DE_MENSAGENS = 20


def montar_historico(mensagens: Sequence[Mensagem]) -> list[MensagemDoModelo]:
    recentes = list(mensagens[-JANELA_DE_MENSAGENS:])

    # O corte da janela pode cair logo depois de uma pergunta, deixando a
    # resposta órfã na frente. O histórico precisa abrir com o usuário.
    while recentes and recentes[0].papel != PapelDaMensagem.USUARIO:
        recentes.pop(0)

    return [
        MensagemDoModelo(
            papel="usuario" if m.papel == PapelDaMensagem.USUARIO else "assistente",
            conteudo=m.conteudo,
        )
        for m in recentes
    ]
