import time
import uuid

from redis.asyncio import Redis

# Janela deslizante: os pedidos velhos saem antes da contagem, então o limite
# não zera de repente na virada do minuto — o que deixaria passar o dobro num
# intervalo curto, como acontece com janela fixa.
_JANELA_DESLIZANTE = """
local agora = tonumber(ARGV[1])
local janela_ms = tonumber(ARGV[2])
local limite = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, agora - janela_ms)
if redis.call('ZCARD', KEYS[1]) >= limite then
  return 0
end

redis.call('ZADD', KEYS[1], agora, ARGV[4])
redis.call('PEXPIRE', KEYS[1], janela_ms)
return 1
"""


class LimitadorDeTaxa:
    def __init__(self, redis: Redis, limite: int, janela_segundos: int) -> None:
        self._limite = limite
        self._janela_ms = janela_segundos * 1000
        self._script = redis.register_script(_JANELA_DESLIZANTE)

    async def permitir(self, chave: str) -> bool:
        agora = int(time.time() * 1000)
        # O membro precisa ser único: dois pedidos no mesmo milissegundo
        # sobrescreveriam um ao outro no conjunto ordenado.
        permitido = await self._script(
            keys=[f"taxa:{chave}"],
            args=[agora, self._janela_ms, self._limite, str(uuid.uuid4())],
        )
        return bool(permitido)
