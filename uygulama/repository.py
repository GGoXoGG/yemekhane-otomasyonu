from database import islem, sorgu, yaz, yordam


def giris_hesabi(eposta):
    return sorgu(
        "SELECT id, sifre_hash, aktif FROM kullanicilar WHERE eposta = %s",
        (eposta,), yazma=True, tek=True,
    )


def kullanici(kullanici_id):
    return sorgu(
        "SELECT id, ad, soyad, eposta, rol, bakiye FROM kullanicilar WHERE id = %s AND aktif = 1",
        (kullanici_id,), yazma=True, tek=True,
    )


def yemekhaneler():
    return sorgu("SELECT id, ad FROM yemekhaneler ORDER BY id")


def ogunler():
    return sorgu("SELECT id, ad FROM ogunler ORDER BY sira")


def menuler(kullanici_id, rol, baslangic, gun_sayisi, yemekhane_id, ogun_id):
    satirlar = sorgu(
        """
        SELECT m.id AS menu_id, d.tarih, d.yemekhane, d.ogun, d.bos_yer, d.rezervasyon_son,
               IF(%s = 'ogrenci', m.ogrenci_fiyati, m.personel_fiyati) AS fiyat,
               o.ad IN ('Öğle', 'Akşam') AS yarim_uygun,
               r.durum AS rezervasyon_durumu,
               NOW() < d.rezervasyon_son AND d.bos_yer > 0
                   AND COALESCE(r.durum, 'iptal') = 'iptal' AS rezerve_edilebilir,
               CASE WHEN NOW() >= d.rezervasyon_son THEN 'Süre doldu'
                    WHEN r.durum IN ('aktif', 'kullanildi') THEN 'Rezervasyon var'
                    WHEN d.bos_yer <= 0 THEN 'Yer kalmadı'
                    ELSE NULL END AS rezervasyon_notu,
               y.yemek_id, y.yemek, y.kategori, y.kalori, y.vejetaryen, y.alerjenler
          FROM v_menu_doluluk d
          JOIN menuler m ON m.id = d.menu_id
          JOIN ogunler o ON o.id = d.ogun_id
          LEFT JOIN v_menu_detay y ON y.menu_id = m.id
          LEFT JOIN rezervasyonlar r ON r.menu_id = m.id AND r.kullanici_id = %s
         WHERE d.tarih BETWEEN COALESCE(%s, CURDATE())
                           AND DATE_ADD(COALESCE(%s, CURDATE()), INTERVAL %s DAY)
           AND (%s IS NULL OR d.yemekhane_id = %s)
           AND (%s IS NULL OR d.ogun_id = %s)
         ORDER BY d.tarih, o.sira, d.yemekhane_id, y.kategori_sira, y.yemek
        """,
        (rol, kullanici_id, baslangic, baslangic, gun_sayisi - 1,
         yemekhane_id, yemekhane_id, ogun_id, ogun_id),
    )
    return _menuleri_topla(satirlar)


def _menuleri_topla(satirlar):
    menuler = {}
    yemek_alanlari = ("yemek_id", "yemek", "kategori", "kalori", "vejetaryen", "alerjenler")
    for satir in satirlar:
        yemek = {alan: satir.pop(alan) for alan in yemek_alanlari}
        menu = menuler.setdefault(satir["menu_id"], {**satir, "yemekler": [], "toplam_kalori": 0})
        if yemek["yemek_id"] is not None:
            yemek["vejetaryen"] = bool(yemek["vejetaryen"])
            menu["yemekler"].append(yemek)
            menu["toplam_kalori"] += yemek["kalori"]
        if "rezerve_edilebilir" in menu:
            menu["rezerve_edilebilir"] = bool(menu["rezerve_edilebilir"])
    return list(menuler.values())


def gunluk_menu(tarih, yemekhane_id, ogun_id):
    satirlar = sorgu(
        """
        SELECT m.id AS menu_id, m.tarih, m.yemekhane_id, yh.ad AS yemekhane,
               m.ogun_id, o.ad AS ogun, y.yemek_id, y.yemek, y.kategori,
               y.kalori, y.vejetaryen, y.alerjenler
          FROM menuler m
          JOIN yemekhaneler yh ON yh.id = m.yemekhane_id
          JOIN ogunler o ON o.id = m.ogun_id
          LEFT JOIN v_menu_detay y ON y.menu_id = m.id
         WHERE m.tarih = %s AND m.yemekhane_id = %s AND m.ogun_id = %s
         ORDER BY y.kategori_sira, y.yemek
        """, (tarih, yemekhane_id, ogun_id),
    )
    menuler = _menuleri_topla(satirlar)
    return menuler[0] if menuler else None


def replika_guncel_mi():
    gtid = sorgu("SELECT @@GLOBAL.gtid_executed AS gtid", yazma=True, tek=True)["gtid"]
    return sorgu(
        "SELECT WAIT_FOR_EXECUTED_GTID_SET(%s, 1) AS sonuc", (gtid,), tek=True,
    )["sonuc"] == 0


def menu_kimligi(menu_id):
    menu = sorgu(
        "SELECT tarih, yemekhane_id, ogun_id FROM menuler WHERE id = %s",
        (menu_id,), yazma=True, tek=True,
    )
    return (menu["tarih"], menu["yemekhane_id"], menu["ogun_id"]) if menu else None


def rezervasyonlar(kullanici_id):
    return sorgu(
        """
        SELECT r.id, r.menu_id, d.tarih, d.yemekhane, d.ogun, r.ucret, r.durum, r.porsiyon,
               d.rezervasyon_son, r.durum = 'aktif' AND NOW() < d.rezervasyon_son AS iptal_edilebilir
          FROM rezervasyonlar r
          JOIN v_menu_doluluk d ON d.menu_id = r.menu_id
         WHERE r.kullanici_id = %s
         ORDER BY d.tarih DESC, d.ogun_id DESC, r.id DESC
        """, (kullanici_id,),
    )


def rezervasyon_yap(kullanici_id, menu_id, porsiyon):
    sonuc = yordam("CALL sp_rezervasyon_yap(%s, %s, %s)", (kullanici_id, menu_id, porsiyon))
    durum = sorgu(
        "SELECT bos_yer FROM v_menu_doluluk WHERE menu_id = %s", (menu_id,), yazma=True, tek=True,
    )
    return {**sonuc, **durum}


def rezervasyon_iptal(kullanici_id, rezervasyon_id):
    return yordam("CALL sp_rezervasyon_iptal(%s, %s)", (kullanici_id, rezervasyon_id))


def bakiye_hareketleri(kullanici_id):
    return sorgu(
        """
        SELECT id, tur, tutar, aciklama, olusturma FROM bakiye_hareketleri
         WHERE kullanici_id = %s ORDER BY olusturma DESC, id DESC
        """, (kullanici_id,),
    )


def bakiye_yukle(kullanici_id, tutar):
    return yordam("CALL sp_bakiye_yukle(%s, %s)", (kullanici_id, tutar))


def degerlendirmeler(kullanici_id):
    return sorgu(
        """
        SELECT r.menu_id, d.tarih, d.yemekhane, d.ogun, y.puan, y.yorum
          FROM rezervasyonlar r
          JOIN v_menu_doluluk d ON d.menu_id = r.menu_id
          LEFT JOIN degerlendirmeler y ON y.menu_id = r.menu_id AND y.kullanici_id = r.kullanici_id
         WHERE r.kullanici_id = %s AND r.durum = 'kullanildi'
         ORDER BY d.tarih DESC, r.menu_id DESC
        """, (kullanici_id,),
    )


def degerlendirme_ekle(kullanici_id, menu_id, puan, yorum):
    return yaz(
        """
        INSERT INTO degerlendirmeler (kullanici_id, menu_id, puan, yorum)
        SELECT kullanici_id, menu_id, %s, %s FROM rezervasyonlar
         WHERE kullanici_id = %s AND menu_id = %s AND durum = 'kullanildi'
        """, (puan, yorum, kullanici_id, menu_id),
    )


def yemekler():
    return sorgu(
        """
        SELECT y.id, y.ad, k.ad AS kategori FROM yemekler y
          JOIN yemek_kategorileri k ON k.id = y.kategori_id
         ORDER BY k.sira, y.ad
        """
    )


def yonetici_menuleri():
    satirlar = sorgu(
        """
        SELECT m.id, m.tarih, d.yemekhane_id, d.yemekhane, d.ogun_id, d.ogun,
               m.ogrenci_fiyati, m.personel_fiyati, my.yemek_id
          FROM menuler m JOIN v_menu_doluluk d ON d.menu_id = m.id
          LEFT JOIN menu_yemekleri my ON my.menu_id = m.id
         ORDER BY m.tarih DESC, d.yemekhane_id, d.ogun_id, my.yemek_id
        """
    )
    menuler = {}
    for satir in satirlar:
        yemek_id = satir.pop("yemek_id")
        menu = menuler.setdefault(satir["id"], {**satir, "yemek_idleri": []})
        if yemek_id is not None:
            menu["yemek_idleri"].append(yemek_id)
    return list(menuler.values())


def menu_kaydet(fiyatlar, yemek_idleri, *, menu_id=None, yeni_menu=None):
    with islem() as cursor:
        if menu_id is None:
            cursor.execute(
                """
                INSERT INTO menuler (tarih, yemekhane_id, ogun_id, ogrenci_fiyati, personel_fiyati)
                VALUES (%s, %s, %s, %s, %s)
                """, (*yeni_menu, *fiyatlar),
            )
            menu_id = cursor.lastrowid
        else:
            cursor.execute("SELECT id FROM menuler WHERE id = %s FOR UPDATE", (menu_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                "UPDATE menuler SET ogrenci_fiyati = %s, personel_fiyati = %s WHERE id = %s",
                (*fiyatlar, menu_id),
            )
            cursor.execute("DELETE FROM menu_yemekleri WHERE menu_id = %s", (menu_id,))
        cursor.executemany(
            "INSERT INTO menu_yemekleri (menu_id, yemek_id) VALUES (%s, %s)",
            [(menu_id, yemek_id) for yemek_id in yemek_idleri],
        )
        return menu_id


def raporlar():
    return sorgu(
        """
        SELECT d.menu_id, d.tarih, d.yemekhane, d.ogun, d.kapasite, d.rezerve,
               d.bos_yer, d.doluluk_yuzde, p.ortalama_puan, p.oy_sayisi
          FROM v_menu_doluluk d JOIN v_menu_puan p ON p.menu_id = d.menu_id
         ORDER BY d.tarih DESC, d.yemekhane_id, d.ogun_id
        """
    )


def saglik():
    sql = "SELECT @@server_id AS server_id, @@global.read_only AS read_only"
    return {"primary": sorgu(sql, yazma=True, tek=True), "replica": sorgu(sql, tek=True)}



def profil_alerjenleri(kullanici_id):
    return sorgu(
        """
        SELECT a.id, a.ad, ka.kullanici_id IS NOT NULL AS secili
          FROM alerjenler a
          LEFT JOIN kullanici_alerjenleri ka ON ka.alerjen_id = a.id AND ka.kullanici_id = %s
         ORDER BY a.ad
        """, (kullanici_id,), yazma=True,
    )


def profil_alerjenleri_kaydet(kullanici_id, alerjenler):
    with islem() as cursor:
        cursor.execute("SELECT id FROM kullanicilar WHERE id = %s FOR UPDATE", (kullanici_id,))
        cursor.execute("DELETE FROM kullanici_alerjenleri WHERE kullanici_id = %s", (kullanici_id,))
        if alerjenler:
            cursor.executemany(
                "INSERT INTO kullanici_alerjenleri (kullanici_id, alerjen_id) VALUES (%s, %s)",
                [(kullanici_id, alerjen_id) for alerjen_id in alerjenler],
            )


def alerjen_eslesmeleri(kullanici_id):
    satirlar = sorgu(
        """
        SELECT ya.yemek_id, a.ad FROM kullanici_alerjenleri ka
          JOIN yemek_alerjenleri ya ON ya.alerjen_id = ka.alerjen_id
          JOIN alerjenler a ON a.id = ka.alerjen_id
         WHERE ka.kullanici_id = %s ORDER BY a.ad
        """, (kullanici_id,), yazma=True,
    )
    eslesmeler = {}
    for satir in satirlar:
        eslesmeler.setdefault(satir["yemek_id"], []).append(satir["ad"])
    return eslesmeler
