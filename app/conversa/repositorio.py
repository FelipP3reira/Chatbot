import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversa.modelos import Conversa, Mensagem, PapelDaMensagem


class RepositorioDeConversas:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def criar_conversa(self) -> Conversa:
        conversa = Conversa()
        self._sessao.add(conversa)
        await self._sessao.commit()
        return conversa

    async def buscar_conversa(self, conversa_id: uuid.UUID) -> Conversa | None:
        return await self._sessao.get(Conversa, conversa_id)

    async def listar_mensagens(self, conversa_id: uuid.UUID) -> list[Mensagem]:
        consulta = (
            select(Mensagem).where(Mensagem.conversa_id == conversa_id).order_by(Mensagem.ordem)
        )
        return list((await self._sessao.scalars(consulta)).all())

    async def registrar_troca(
        self,
        conversa_id: uuid.UUID,
        pergunta: str,
        resposta: str,
        tokens_entrada: int = 0,
        tokens_saida: int = 0,
    ) -> None:
        """Grava pergunta e resposta juntas: ou as duas entram, ou nenhuma."""
        proxima = await self._proxima_ordem(conversa_id)
        self._sessao.add_all(
            [
                Mensagem(
                    conversa_id=conversa_id,
                    ordem=proxima,
                    papel=PapelDaMensagem.USUARIO,
                    conteudo=pergunta,
                ),
                Mensagem(
                    conversa_id=conversa_id,
                    ordem=proxima + 1,
                    papel=PapelDaMensagem.ASSISTENTE,
                    conteudo=resposta,
                ),
            ]
        )
        # Soma no banco, não em Python: duas respostas concorrentes na mesma
        # conversa não podem sobrescrever a contagem uma da outra.
        await self._sessao.execute(
            update(Conversa)
            .where(Conversa.id == conversa_id)
            .values(
                tokens_entrada=Conversa.tokens_entrada + tokens_entrada,
                tokens_saida=Conversa.tokens_saida + tokens_saida,
            )
        )
        await self._sessao.commit()

    async def _proxima_ordem(self, conversa_id: uuid.UUID) -> int:
        consulta = select(func.coalesce(func.max(Mensagem.ordem), -1)).where(
            Mensagem.conversa_id == conversa_id
        )
        maior = await self._sessao.scalar(consulta)
        return int(maior if maior is not None else -1) + 1
