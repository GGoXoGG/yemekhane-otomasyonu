import os

from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

redis = Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
    retry=Retry(NoBackoff(), 0),
)
