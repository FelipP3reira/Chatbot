from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.chunker import dividir_em_trechos
from app.rag.embeddings import Embedder
from app.rag.modelos import Documento, Trecho

TRECHOS_RECUPERADOS = 4

# Distância do cosseno (0 = idêntico, 2 = oposto). Acima disso o trecho fala de
# outro assunto, e enfiá-lo no prompt só atrapalha a resposta. O valor depende
# do embedder: medindo pergunta pertinente x pergunta de outro assunto, o
# MiniLM dá 0,32 x 0,69 e o de hashing 0,34 x 0,88 — 0,5 separa os dois casos.
DISTANCIA_MAXIMA = 0.5


@dataclass(frozen=True)
class TrechoRecuperado:
    titulo_do_documento: str
    conteudo: str
    distancia: float


class IndiceDeDocumentos:
    def __init__(self, sessao: AsyncSession, embedder: Embedder) -> None:
        self._sessao = sessao
        self._embedder = embedder

    async def ingerir(self, titulo: str, conteudo: str, origem: str | None = None) -> Documento:
        pedacos = dividir_em_trechos(conteudo)
        vetores = await self._embedder.codificar(pedacos)

        documento = Documento(titulo=titulo, origem=origem)
        documento.trechos = [
            Trecho(ordem=ordem, conteudo=pedaco, embedding=vetor)
            for ordem, (pedaco, vetor) in enumerate(zip(pedacos, vetores, strict=True))
        ]
        self._sessao.add(documento)
        await self._sessao.commit()
        return documento

    async def buscar(
        self, pergunta: str, limite: int = TRECHOS_RECUPERADOS
    ) -> list[TrechoRecuperado]:
        (vetor,) = await self._embedder.codificar([pergunta])

        # O alias não pode aparecer no WHERE, então a expressão é reaproveitada.
        # O JOIN traz o título junto: carregar o relacionamento depois seria
        # lazy load, que estoura numa sessão assíncrona.
        distancia = Trecho.embedding.cosine_distance(vetor)
        consulta = (
            select(Documento.titulo, Trecho.conteudo, distancia.label("distancia"))
            .join(Documento, Trecho.documento_id == Documento.id)
            .where(distancia <= DISTANCIA_MAXIMA)
            .order_by(distancia)
            .limit(limite)
        )

        resultado = await self._sessao.execute(consulta)
        return [
            TrechoRecuperado(titulo_do_documento=titulo, conteudo=conteudo, distancia=float(valor))
            for titulo, conteudo, valor in resultado.all()
        ]

    async def listar_documentos(self) -> list[Documento]:
        consulta = select(Documento).order_by(Documento.criado_em.desc())
        return list((await self._sessao.scalars(consulta)).all())
