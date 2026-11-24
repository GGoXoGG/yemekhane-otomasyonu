from secrets import token_urlsafe
from threading import Lock
from time import monotonic

CUKUR = "yemekhane_oturum"
SURE = 30 * 60
_oturumlar = {}
_kilit = Lock()


def ac(kullanici_id, eski_token=None):
    simdi = monotonic()
    token = token_urlsafe(32)
    oturum = {"kullanici_id": kullanici_id, "csrf": token_urlsafe(32), "son": simdi + SURE}
    with _kilit:
        for anahtar, kayit in list(_oturumlar.items()):
            if kayit["son"] <= simdi:
                _oturumlar.pop(anahtar)
        _oturumlar.pop(eski_token, None)
        _oturumlar[token] = oturum
    return token


def getir(token):
    with _kilit:
        kayit = _oturumlar.get(token)
        if kayit and kayit["son"] > monotonic():
            return kayit
        _oturumlar.pop(token, None)
        return None


def kapat(token):
    with _kilit:
        _oturumlar.pop(token, None)
