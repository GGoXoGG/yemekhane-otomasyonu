import json
from datetime import datetime, time, timedelta
from threading import Lock
from zoneinfo import ZoneInfo

from flask import current_app
from redis.exceptions import RedisError
from werkzeug.exceptions import ServiceUnavailable

import repository as repo
from redis_baglanti import redis

ISTANBUL = ZoneInfo("Europe/Istanbul")
BEKLEYEN = "menu_bekleyen"
_menu_kilidi = Lock()


def menu_anahtari(tarih, yemekhane_id, ogun_id):
    return f"menu:{yemekhane_id}:{tarih.isoformat()}:{ogun_id}"


def gunluk_menuler(yemekhane_id, ogun_id):
    bugun = datetime.now(ISTANBUL).date()
    yarin = datetime.combine(bugun + timedelta(days=1), time.min, ISTANBUL)
    yerler = [yemekhane_id] if yemekhane_id else [yer["id"] for yer in repo.yemekhaneler()]
    ogunler = [ogun_id] if ogun_id else [ogun["id"] for ogun in repo.ogunler()]
    menuler = []
    for ogun in ogunler:
        for yer in yerler:
            menu = _menu_getir(bugun, yer, ogun, yarin)
            if menu is not None:
                menuler.append(menu)
    return menuler


def _menu_getir(tarih, yemekhane_id, ogun_id, son):
    anahtar = menu_anahtari(tarih, yemekhane_id, ogun_id)
    with _menu_kilidi:
        with redis.pipeline(transaction=False) as istek:
            bekliyor, kayit = istek.sismember(BEKLEYEN, anahtar).get(anahtar).execute()
        if bekliyor:
            _sil(anahtar)
        elif kayit is not None:
            current_app.logger.info("CACHE HIT %s", anahtar)
            return json.loads(kayit)

        current_app.logger.info("CACHE MISS %s", anahtar)
        if not repo.replika_guncel_mi():
            current_app.logger.warning("CACHE WAIT TIMEOUT %s", anahtar)
            raise ServiceUnavailable("Menü henüz replikaya ulaşmadı. Biraz sonra tekrar deneyin.")
        menu = repo.gunluk_menu(tarih, yemekhane_id, ogun_id)
        if menu is not None and datetime.now(ISTANBUL) < son:
            redis.set(anahtar, current_app.json.dumps(menu), exat=int(son.timestamp()))
        return menu


def menu_kaydet(fiyatlar, yemekler, menu_id=None, yeni_menu=None):
    with _menu_kilidi:
        kimlik = yeni_menu if yeni_menu else repo.menu_kimligi(menu_id)
        if kimlik is None:
            return None
        anahtar = menu_anahtari(*kimlik)
        # Commit sonrası Redis kesilirse eski menü HIT olarak dönmemeli.
        yeni_isaret = redis.sadd(BEKLEYEN, anahtar)
        try:
            sonuc = repo.menu_kaydet(fiyatlar, yemekler, menu_id=menu_id, yeni_menu=yeni_menu)
        except Exception:
            if yeni_isaret:
                try:
                    redis.srem(BEKLEYEN, anahtar)
                except RedisError:
                    current_app.logger.warning("CACHE CLEANUP WAIT %s", anahtar)
            raise
        try:
            _sil(anahtar)
        except RedisError:
            current_app.logger.warning("CACHE DELETE WAIT %s", anahtar)
        return sonuc


def _sil(anahtar):
    with redis.pipeline() as istek:
        istek.delete(anahtar).srem(BEKLEYEN, anahtar).execute()
    current_app.logger.info("CACHE DELETE %s", anahtar)
