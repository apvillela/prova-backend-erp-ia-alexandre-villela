import logging

from redis.exceptions import RedisError

from erp_api import config
from erp_api.caching.client import get_redis_async_client

settings = config.get_settings()

log = logging.getLogger(__name__)


def _version_key(namespace: str) -> str:
    return f"cache:{namespace}:versao"


async def _current_version(namespace: str) -> int:
    value = await get_redis_async_client().get(_version_key(namespace))
    return int(value) if value else 0


async def get_cached(namespace: str, key: str) -> str | None:
    try:
        version = await _current_version(namespace)
        value: str | None = await get_redis_async_client().get(
            f"cache:{namespace}:v{version}:{key}"
        )
    except (RedisError, OSError) as e:
        log.warning(f"Cache indisponível na leitura ({type(e).__name__}); seguindo sem cache")
        return None
    return value


async def set_cached(namespace: str, key: str, value: str, ttl: float) -> None:
    try:
        version = await _current_version(namespace)
        await get_redis_async_client().set(
            f"cache:{namespace}:v{version}:{key}", value, ex=int(ttl)
        )
    except (RedisError, OSError) as e:
        log.warning(f"Cache indisponível na escrita ({type(e).__name__}); seguindo sem cache")


async def hit_rate_limit(key: str, max_hits: int, window_s: int) -> int | None:
    """Janela fixa via INCR+EXPIRE; retorna segundos até liberar quando estoura o limite.

    Se o Redis estiver fora, não limita (fail-open): o endpoint continua funcionando.
    """
    full_key = f"ratelimit:{key}"
    try:
        redis = get_redis_async_client()
        hits = await redis.incr(full_key)
        if hits == 1:
            await redis.expire(full_key, window_s)
        if hits > max_hits:
            ttl = await redis.ttl(full_key)
            return max(int(ttl), 1)
    except (RedisError, OSError) as e:
        log.warning(f"Rate limit indisponível ({type(e).__name__}); seguindo sem limitar")
    return None


async def invalidate_namespace(namespace: str) -> None:
    """Invalidação por versão: escrever bumpa a versão e as chaves antigas expiram pelo TTL.

    Evita varrer chaves com SCAN/DEL a cada escrita, que é O(n) no Redis.
    """
    try:
        await get_redis_async_client().incr(_version_key(namespace))
    except (RedisError, OSError) as e:
        log.warning(f"Cache indisponível na invalidação ({type(e).__name__})")
