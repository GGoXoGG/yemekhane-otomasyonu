import json
from secrets import token_urlsafe

from redis_baglanti import redis

CUKUR = "yemekhane_oturum"
SURE = 1800


def ac(kullanici_id, eski_token=None):
    token = token_urlsafe(32)
    kayit = json.dumps({"kullanici_id": kullanici_id, "csrf": token_urlsafe(32)})
    with redis.pipeline() as istek:
        istek.set(f"oturum:{token}", kayit, ex=SURE)
        if eski_token:
            istek.delete(f"oturum:{eski_token}")
        istek.execute()
    return token


def getir(token):
    if not token:
        return None
    kayit = redis.get(f"oturum:{token}")
    return json.loads(kayit) if kayit else None


def yenile(token):
    return redis.expire(f"oturum:{token}", SURE)


def kapat(token):
    if token:
        redis.delete(f"oturum:{token}")


def cerez_yaz(yanit, token, guvenli):
    yanit.set_cookie(
        CUKUR, token, max_age=SURE, httponly=True, secure=guvenli, samesite="Lax", path="/api",
    )
