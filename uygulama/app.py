from datetime import date, datetime, time, timedelta
from hmac import compare_digest

from flask import Flask, g, jsonify, request
from flask.json.provider import DefaultJSONProvider
from mysql.connector import Error
from werkzeug.exceptions import Forbidden, HTTPException, Unauthorized, UnsupportedMediaType

from api import api
import oturum
import repository as repo


class YemekhaneJSON(DefaultJSONProvider):
    @staticmethod
    def default(deger):
        if isinstance(deger, (date, datetime, time)):
            return deger.isoformat()
        if isinstance(deger, timedelta):
            return str(deger)
        return DefaultJSONProvider.default(deger)


app = Flask(__name__)
app.json = YemekhaneJSON(app)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.register_blueprint(api)


@app.before_request
def api_kontrolu():
    if request.endpoint in (None, "api.saglik"):
        return
    yazma = request.method in ("POST", "PUT")
    if yazma:
        origin = request.headers.get("Origin")
        if origin is not None and origin != request.host_url.rstrip("/"):
            raise Forbidden("İstek kaynağı geçersiz.")
        if not request.is_json:
            raise UnsupportedMediaType("JSON içerik gönderin.")
    if request.endpoint == "api.giris":
        return
    g.oturum = oturum.getir(request.cookies.get(oturum.CUKUR))
    if g.oturum is None:
        raise Unauthorized("Oturum açmanız gerekiyor.")
    if yazma and not compare_digest(
        request.headers.get("X-CSRF-Token", "").encode(), g.oturum["csrf"].encode(),
    ):
        raise Forbidden("İstek doğrulanamadı.")
    g.kullanici = repo.kullanici(g.oturum["kullanici_id"])
    if g.kullanici is None:
        oturum.kapat(request.cookies.get(oturum.CUKUR))
        raise Unauthorized("Oturum açmanız gerekiyor.")
    if request.path.startswith("/api/yonetici/") and g.kullanici["rol"] != "yonetici":
        raise Forbidden("Bu işlem için yönetici yetkisi gerekiyor.")


@app.after_request
def onbellek_kontrolu(yanit):
    yanit.headers["Cache-Control"] = "no-store"
    return yanit


@app.errorhandler(HTTPException)
def http_hatasi(hata):
    sabit_mesajlar = {
        404: "İstenen kayıt veya adres bulunamadı.",
        405: "Bu adres için kullanılan HTTP yöntemi geçersiz.",
        413: "Gönderilen veri çok büyük.",
        500: "Sunucuda beklenmeyen bir hata oluştu.",
    }
    mesaj = sabit_mesajlar.get(hata.code, hata.description)
    if hata.code == 404 and request.endpoint is not None:
        mesaj = hata.description
    return jsonify(basarili=False, mesaj=mesaj), hata.code


@app.errorhandler(Error)
def veritabani_hatasi(hata):
    if hata.errno == 1644 and hata.sqlstate == "45000":
        return jsonify(basarili=False, mesaj=hata.msg), 400
    app.logger.error("MySQL hatası (%s): %s", hata.errno, hata.msg)
    return jsonify(basarili=False, mesaj="Veritabanı işlemi tamamlanamadı."), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
