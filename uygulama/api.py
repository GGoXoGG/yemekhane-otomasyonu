from datetime import date
from decimal import Decimal, InvalidOperation

import bcrypt
from flask import Blueprint, g, jsonify, request
from mysql.connector import Error
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized

import onbellek
import oturum
import repository as repo
from redis_baglanti import redis

api = Blueprint("api", __name__, url_prefix="/api")


def veri_al():
    veri = request.get_json(silent=True)
    if not isinstance(veri, dict):
        raise BadRequest("JSON nesnesi gönderin.")
    return veri


def kimlik(deger, alan, en_buyuk=4294967295):
    if type(deger) is int:
        sayi = deger
    elif isinstance(deger, str) and deger.isascii() and deger.isdecimal() and len(deger) <= 10:
        sayi = int(deger)
    else:
        sayi = 0
    if not 1 <= sayi <= en_buyuk:
        raise BadRequest(f"{alan} geçersiz.")
    return sayi


def tarih(deger):
    try:
        gun = date.fromisoformat(deger)
        if gun.year >= 1000 and gun.isoformat() == deger:
            return gun
    except (TypeError, ValueError):
        pass
    raise BadRequest("Geçerli bir tarih girin.")


def para(deger, en_az, en_cok, hata):
    try:
        sayi = Decimal(str(deger))
        if sayi.is_finite() and en_az <= sayi <= en_cok and sayi == sayi.quantize(Decimal("0.01")):
            return sayi
    except InvalidOperation:
        pass
    raise BadRequest(hata)


@api.get("/saglik")
def saglik():
    durum = repo.saglik()
    durum["redis"] = redis.ping()
    saglikli = (
        durum["redis"]
        and durum["primary"]["server_id"] != durum["replica"]["server_id"]
        and not durum["primary"]["read_only"] and durum["replica"]["read_only"]
    )
    return jsonify(basarili=bool(saglikli), **durum), 200 if saglikli else 503


@api.post("/giris")
def giris():
    veri = veri_al()
    eposta = veri.get("eposta")
    sifre = veri.get("sifre")
    if not isinstance(eposta, str) or not isinstance(sifre, str):
        raise BadRequest("E-posta ve şifre girin.")
    eposta = eposta.strip().lower()
    kodlu_sifre = sifre.encode("utf-8")
    if not eposta or len(eposta) > 120 or not 0 < len(kodlu_sifre) <= 72:
        raise Unauthorized("E-posta veya şifre hatalı.")
    hesap = repo.giris_hesabi(eposta)
    if not hesap or not hesap["aktif"] or not bcrypt.checkpw(kodlu_sifre, hesap["sifre_hash"].encode()):
        raise Unauthorized("E-posta veya şifre hatalı.")
    token = oturum.ac(hesap["id"], request.cookies.get(oturum.CUKUR))
    yanit = jsonify(basarili=True)
    oturum.cerez_yaz(yanit, token, request.is_secure)
    return yanit


@api.post("/cikis")
def cikis():
    oturum.kapat(request.cookies.get(oturum.CUKUR))
    yanit = jsonify(basarili=True)
    yanit.delete_cookie(oturum.CUKUR, path="/api", httponly=True, secure=request.is_secure, samesite="Lax")
    return yanit


@api.get("/oturum")
def oturum_bilgisi():
    return jsonify(basarili=True, kullanici=g.kullanici, csrf=g.oturum["csrf"])


@api.get("/yemekhaneler")
def yemekhaneler():
    return jsonify(basarili=True, yemekhaneler=repo.yemekhaneler())


@api.get("/ogunler")
def ogunler():
    return jsonify(basarili=True, ogunler=repo.ogunler())


@api.get("/menu/gunluk")
@api.get("/menu/haftalik")
def menu_listesi():
    yemekhane = request.args.get("yemekhane_id")
    ogun = request.args.get("ogun_id")
    yer_id = kimlik(yemekhane, "Yemekhane", 255) if yemekhane is not None else None
    ogun_id = kimlik(ogun, "Öğün", 255) if ogun is not None else None
    if request.path.endswith("/gunluk"):
        menuler = onbellek.gunluk_menuler(yer_id, ogun_id)
    else:
        baslangic = request.args.get("baslangic")
        ilk_gun = tarih(baslangic) if baslangic is not None else None
        menuler = repo.menuler(g.kullanici["id"], g.kullanici["rol"], ilk_gun, 7, yer_id, ogun_id)
    return jsonify(basarili=True, menuler=menuler)


@api.get("/rezervasyonlar")
def rezervasyon_listesi():
    return jsonify(basarili=True, rezervasyonlar=repo.rezervasyonlar(g.kullanici["id"]))


@api.post("/rezervasyonlar")
def rezervasyon_yap():
    menu_id = kimlik(veri_al().get("menu_id"), "Menü")
    sonuc = repo.rezervasyon_yap(g.kullanici["id"], menu_id)
    return jsonify(basarili=True, mesaj="Rezervasyon yapıldı.", durum="aktif", **sonuc), 201


@api.post("/rezervasyonlar/<int:rezervasyon_id>/iptal")
def rezervasyon_iptal(rezervasyon_id):
    sonuc = repo.rezervasyon_iptal(g.kullanici["id"], kimlik(rezervasyon_id, "Rezervasyon"))
    return jsonify(basarili=True, mesaj="Rezervasyon iptal edildi.", durum="iptal", **sonuc)


@api.get("/bakiye")
def bakiye():
    return jsonify(basarili=True, bakiye=g.kullanici["bakiye"])


@api.get("/bakiye/hareketler")
def bakiye_hareketleri():
    return jsonify(basarili=True, hareketler=repo.bakiye_hareketleri(g.kullanici["id"]))


@api.post("/bakiye/yukle")
def bakiye_yukle():
    sinir = Decimal("99999999.99")
    tutar = para(veri_al().get("tutar"), -sinir, sinir, "Geçerli bir yükleme tutarı girin.")
    sonuc = repo.bakiye_yukle(g.kullanici["id"], tutar)
    return jsonify(basarili=True, mesaj="Bakiye yüklendi.", **sonuc), 201


@api.get("/degerlendirmeler")
def degerlendirme_listesi():
    return jsonify(basarili=True, degerlendirmeler=repo.degerlendirmeler(g.kullanici["id"]))


@api.post("/degerlendirmeler")
def degerlendirme_ekle():
    veri = veri_al()
    menu_id = kimlik(veri.get("menu_id"), "Menü")
    puan = kimlik(veri.get("puan"), "Puan (1–5)", 5)
    yorum = veri.get("yorum", "")
    if not isinstance(yorum, str) or len(yorum) > 500:
        raise BadRequest("Yorum en fazla 500 karakter olabilir.")
    try:
        yazildi = repo.degerlendirme_ekle(g.kullanici["id"], menu_id, puan, yorum.strip() or None)
    except Error as hata:
        if hata.errno == 1062:
            raise BadRequest("Bu menüyü zaten değerlendirdiniz.") from hata
        raise
    if not yazildi:
        raise BadRequest("Yalnızca kullandığınız menüleri değerlendirebilirsiniz.")
    return jsonify(basarili=True, mesaj="Değerlendirmeniz kaydedildi."), 201


@api.get("/yonetici/yemekler")
def yonetici_yemekleri():
    return jsonify(basarili=True, yemekler=repo.yemekler())


@api.get("/yonetici/menuler")
def yonetici_menuleri():
    return jsonify(basarili=True, menuler=repo.yonetici_menuleri())


@api.post("/yonetici/menuler")
@api.put("/yonetici/menuler/<int:menu_id>")
def menu_kaydet(menu_id=None):
    veri = veri_al()
    fiyatlar = tuple(
        para(veri.get(alan), 0, Decimal("999999.99"), f"Geçerli {etiket} fiyatı girin.")
        for alan, etiket in (("ogrenci_fiyati", "öğrenci"), ("personel_fiyati", "personel"))
    )
    yemek_idleri = veri.get("yemek_idleri")
    if not isinstance(yemek_idleri, list) or not yemek_idleri:
        raise BadRequest("En az bir yemek seçin.")
    yemekler = [kimlik(yemek_id, "Yemek", 65535) for yemek_id in yemek_idleri]
    if len(set(yemekler)) != len(yemekler):
        raise BadRequest("Aynı yemek bir kez seçilebilir.")
    yeni_menu = None
    if menu_id is None:
        yeni_menu = (
            tarih(veri.get("tarih")), kimlik(veri.get("yemekhane_id"), "Yemekhane", 255),
            kimlik(veri.get("ogun_id"), "Öğün", 255),
        )
    else:
        kimlik(menu_id, "Menü")
    try:
        sonuc = onbellek.menu_kaydet(fiyatlar, yemekler, menu_id=menu_id, yeni_menu=yeni_menu)
    except Error as hata:
        if hata.errno == 1062:
            raise BadRequest("Bu tarih, yemekhane ve öğün için zaten bir menü var.") from hata
        if hata.errno == 1452:
            raise BadRequest("Geçerli bir yemekhane, öğün ve yemek seçin.") from hata
        raise
    if sonuc is None:
        raise NotFound("Menü bulunamadı.")
    return jsonify(basarili=True, mesaj="Menü kaydedildi.", menu_id=sonuc), 201 if yeni_menu else 200


@api.get("/yonetici/raporlar")
def yonetici_raporlari():
    return jsonify(basarili=True, raporlar=repo.raporlar())
