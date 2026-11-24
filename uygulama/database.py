import os
from contextlib import contextmanager

import mysql.connector


def baglan(yazma=False, autocommit=True):
    host = "DB_YAZMA_HOST" if yazma else "DB_OKUMA_HOST"
    return mysql.connector.connect(
        host=os.environ[host],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_ADI"],
        user=os.environ["DB_KULLANICI"],
        password=os.environ["DB_SIFRE"],
        charset="utf8mb4",
        time_zone="+03:00",
        connection_timeout=4,
        autocommit=autocommit,
    )


def sorgu(sql, parametreler=(), *, yazma=False, tek=False):
    with baglan(yazma) as baglanti, baglanti.cursor(dictionary=True, buffered=True) as cursor:
        cursor.execute(sql, parametreler)
        return cursor.fetchone() if tek else cursor.fetchall()


def yaz(sql, parametreler):
    with baglan(yazma=True) as baglanti, baglanti.cursor() as cursor:
        cursor.execute(sql, parametreler)
        return cursor.rowcount


def yordam(sql, parametreler):
    with baglan(yazma=True) as baglanti, baglanti.cursor(dictionary=True, buffered=True) as cursor:
        cursor.execute(sql, parametreler)
        sonuc = cursor.fetchone()
        while cursor.nextset():
            if cursor.with_rows:
                cursor.fetchall()
        return sonuc


@contextmanager
def islem():
    with baglan(yazma=True, autocommit=False) as baglanti, baglanti.cursor(buffered=True) as cursor:
        try:
            yield cursor
            baglanti.commit()
        except Exception:
            baglanti.rollback()
            raise
