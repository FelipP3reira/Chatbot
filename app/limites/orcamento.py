import uuid

from redis.asyncio import Redis

# Ler e somar em dois comandos deixaria duas requisições simultâneas passarem
# pelo teto ao mesmo tempo. A checagem e a soma acontecem juntas.
_RESERVAR = """
local usados = tonumber(redis.call('GET', KEYS[1]) or '0')
local pedido = tonumber(ARGV[1])
local teto = tonumber(ARGV[2])

if usados + pedido > teto then
  return -1
end

local total = redis.call('INCRBY', KEYS[1], pedido)
redis.call('EXPIRE', KEYS[1], ARGV[3])
return total
"""


class OrcamentoEsgotado(Exception):
    pass


class OrcamentoDeTokens:
    def __init__(self, redis: Redis, teto: int, validade_segundos: int) -> None:
        self._redis = redis
        self._teto = teto
        self._validade = validade_segundos
        self._script = redis.register_script(_RESERVAR)

    async def reservar(self, conversa_id: uuid.UUID, tokens: int) -> int:
        """Soma ao consumo da conversa, ou levanta se estourar o teto."""
        total = await self._script(
            keys=[self._chave(conversa_id)], args=[tokens, self._teto, self._validade]
        )
        if total == -1:
            raise OrcamentoEsgotado
        return int(total)

    async def registrar_consumo(self, conversa_id: uuid.UUID, tokens: int) -> None:
        """Contabiliza tokens já gastos — a resposta não pode ser 'desgerada'
        por ter passado do teto, mas a próxima pergunta será barrada."""
        await self._redis.incrby(self._chave(conversa_id), tokens)
        await self._redis.expire(self._chave(conversa_id), self._validade)

    async def consumidos(self, conversa_id: uuid.UUID) -> int:
        valor = await self._redis.get(self._chave(conversa_id))
        return int(valor) if valor else 0

    def _chave(self, conversa_id: uuid.UUID) -> str:
        return f"orcamento:{conversa_id}"
