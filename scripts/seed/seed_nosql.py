import argparse
import os
from datetime import date, datetime
from decimal import Decimal

import psycopg
import requests
from dotenv import load_dotenv
from psycopg.rows import dict_row
from valkey import Valkey


load_dotenv()

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "gayang")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD")

COUCH_URL = os.getenv("COUCH_URL", "http://127.0.0.1:5984").rstrip("/")
COUCH_DB = os.getenv("COUCH_DB", "gayang")
COUCH_USER = os.getenv("COUCH_USER")
COUCH_PASSWORD = os.getenv("COUCH_PASSWORD")

VALKEY_HOST = os.getenv("VALKEY_HOST", "127.0.0.1")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
VALKEY_DB = int(os.getenv("VALKEY_DB", "0"))


pg = psycopg.connect(
    host=PG_HOST,
    port=PG_PORT,
    dbname=PG_DB,
    user=PG_USER,
    password=PG_PASSWORD,
    row_factory=dict_row,
)

couch = requests.Session()
couch.auth = (COUCH_USER, COUCH_PASSWORD)

vk = Valkey(
    host=VALKEY_HOST,
    port=VALKEY_PORT,
    db=VALKEY_DB,
    decode_responses=True,
)


def json_safe(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: json_safe(x) for k, x in v.items()}
    if isinstance(v, list):
        return [json_safe(x) for x in v]
    return v


def fetch_all(sql, params=None):
    with pg.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def couch_bulk_insert(docs):
    if docs:
        r = couch.post(
            f"{COUCH_URL}/{COUCH_DB}/_bulk_docs",
            json={"docs": json_safe(docs)}
        )
        r.raise_for_status()

# couchdb

def seed_pengguna():
    rows = fetch_all("""
        SELECT 
            u.id_pengguna,
            u.nama,
            u.email,
            u.no_telp,
            u.password_hash,
            u.tanggal_daftar,
            json_agg(
                json_build_object(
                    'id_alamat', a.id_alamat
                )
            ) AS alamat
        FROM pengguna u
        LEFT JOIN alamat a
        ON u.id_pengguna = a.id_pengguna
        GROUP BY u.id_pengguna
    """)

    docs = [
        {
            "_id": f"pengguna:{r['id_pengguna']}",
            "type":"pengguna",
            **r
        }
        for r in rows
    ]

    couch_bulk_insert(docs)


def seed_produk():
    rows = fetch_all("""
        SELECT
            p.*,
            json_build_object(
                'id_kategori', k.id_kategori,
                'nama_kategori', k.nama_kategori
            ) AS kategori
        FROM produk p
        JOIN kategori k
        ON p.id_kategori=k.id_kategori
    """)

    docs=[
        {
            "_id":f"produk:{r['id_produk']}",
            "type":"produk",
            **r
        }
        for r in rows
    ]

    couch_bulk_insert(docs)


def seed_pesanan():
    rows = fetch_all("""
        SELECT
            p.id_pesanan,
            p.id_penjual,
            p.id_pembeli,
            p.id_alamat,
            p.tanggal_pesanan,
            pb.id_pembayaran,
            p.status_pesanan,

            (
                SELECT json_agg(
                    json_build_object(
                        'id_pengiriman', pg.id_pengiriman,
                        'tanggal_kirim', pg.tanggal_kirim,
                        'tanggal_terima', pg.tanggal_terima
                    )
                )
                FROM pengiriman pg
                WHERE pg.id_pesanan=p.id_pesanan
            ) AS pengiriman,


            (
                SELECT json_agg(
                    json_build_object(
                        'no_urut', d.no_urut,
                        'id_produk', d.id_produk,
                        'jenis_transaksi', d.jenis_transaksi,
                        'harga', d.harga
                    )
                )
                FROM detail_pesanan d
                WHERE d.id_pesanan=p.id_pesanan
            ) AS detail_pesanan


        FROM pesanan p

        LEFT JOIN pembayaran pb
        ON pb.id_pesanan=p.id_pesanan
    """)

    docs=[
        {
            "_id":f"pesanan:{r['id_pesanan']}",
            "type":"pesanan",
            **r
        }
        for r in rows
    ]

    couch_bulk_insert(docs)


def seed_penyewaan():
    rows=fetch_all("""
        SELECT
            s.*,
            json_build_object(
                'id_pengembalian',
                g.id_pengembalian,
                'tanggal_pengembalian',
                g.tanggal_pengembalian,
                'status_pengembalian',
                g.status_pengembalian
            ) AS pengembalian
        FROM penyewaan s
        LEFT JOIN pengembalian g
        ON s.id_pengembalian=g.id_pengembalian
    """)

    docs=[
        {
            "_id":f"penyewaan:{r['id_penyewaan']}",
            "type":"penyewaan",
            **r
        }
        for r in rows
    ]

    couch_bulk_insert(docs)


def seed_pengembalian():
    rows = fetch_all("""
        SELECT
            id_pengembalian,
            tanggal_pengembalian,
            kondisi_sebelum,
            kondisi_sesudah,
            hasil_analisis_ai,
            catatan_kerusakan,
            status_pengembalian,
            bukti_foto_video,
            tanda_tangan_digital
        FROM pengembalian
    """)

    docs = [
        {
            "_id": f"pengembalian:{r['id_pengembalian']}",
            "type": "pengembalian",

            "id_pengembalian": r["id_pengembalian"],
            "tanggal_pengembalian": r["tanggal_pengembalian"],
            "kondisi_sebelum": r["kondisi_sebelum"],
            "kondisi_sesudah": r["kondisi_sesudah"],
            "hasil_analisis_ai": r["hasil_analisis_ai"],
            "catatan_kerusakan": r["catatan_kerusakan"],
            "status_pengembalian": r["status_pengembalian"],
            "bukti_foto_video": r["bukti_foto_video"],
            "tanda_tangan_digital": r["tanda_tangan_digital"]
        }
        for r in rows
    ]

    couch_bulk_insert(docs)


def seed_ruang_chat():
    rows=fetch_all("""
        SELECT
            rc.*,
            (
                SELECT json_agg(
                    json_build_object(
                        'id_pesan',pc.id_pesan,
                        'id_pengirim',pc.id_pengirim,
                        'pesan',pc.pesan,
                        'waktu_kirim',pc.waktu_kirim,
                        'status',pc.status
                    )
                )
                FROM pesan_chat pc
                WHERE pc.id_ruang_chat=rc.id_ruang_chat
            ) AS pesan_chat
        FROM ruang_chat rc
    """)

    docs=[
        {
            "_id":f"ruang_chat:{r['id_ruang_chat']}",
            "type":"ruang_chat",
            **r
        }
        for r in rows
    ]

    couch_bulk_insert(docs)

def seed_alamat():
    rows = fetch_all("""
        SELECT
            id_alamat,
            label_alamat,
            nama_penerima,
            no_telp_penerima,
            kota,
            provinsi,
            kode_pos,
            jalan
        FROM alamat
    """)

    docs = [
        {
            "_id": f"alamat:{r['id_alamat']}",
            "type": "alamat",
            **r
        }
        for r in rows
    ]

    couch_bulk_insert(docs)

def seed_pembayaran():

    rows = fetch_all("""
        SELECT
            id_pembayaran,
            id_pesanan,
            metode_pembayaran,
            no_referensi,
            nominal,
            waktu_pembayaran,
            bukti_pembayaran,
            status_pembayaran
        FROM pembayaran
    """)

    docs=[
        {
            "_id":f"pembayaran:{r['id_pembayaran']}",
            "type":"pembayaran",
            **r
        }
        for r in rows
    ]

    couch_bulk_insert(docs)

def seed_ulasan():

    rows = fetch_all("""
        SELECT
            id_ulasan,
            id_produk,
            id_pengguna,
            rating,
            komentar,
            tanggal_ulasan
        FROM ulasan
    """)

    docs=[
        {
            "_id":f"ulasan:{r['id_ulasan']}",
            "type":"ulasan",
            **r
        }
        for r in rows
    ]

    couch_bulk_insert(docs)

def seed_detail_pesanan():

    rows = fetch_all("""
        SELECT
            id_detail,
            no_urut,
            id_produk,
            jenis_transaksi,
            harga
        FROM detail_pesanan
    """)

    docs = [
        {
            "_id": f"detail_pesanan:{r['id_detail']}",
            "type": "detail_pesanan",

            "id_detail": r["id_detail"],
            "no_urut": r["no_urut"],
            "id_produk": r["id_produk"],
            "jenis_transaksi": r["jenis_transaksi"],
            "harga": r["harga"]
        }
        for r in rows
    ]

    couch_bulk_insert(docs)

def seed_pengiriman():

    rows = fetch_all("""
        SELECT
            id_pengiriman,
            kurir,
            no_resi,
            tanggal_kirim,
            tanggal_terima,
            status_pengiriman
        FROM pengiriman
    """)

    docs = [
        {
            "_id": f"pengiriman:{r['id_pengiriman']}",
            "type": "pengiriman",

            "id_pengiriman": r["id_pengiriman"],
            "kurir": r["kurir"],
            "no_resi": r["no_resi"],
            "tanggal_kirim": r["tanggal_kirim"],
            "tanggal_terima": r["tanggal_terima"],
            "status_pengiriman": r["status_pengiriman"]
        }
        for r in rows
    ]

    couch_bulk_insert(docs)


# valkey seeding

def seed_valkey_produk_favorit():

    print("\n=== Valkey: produk favorit ===")

    rows = fetch_all("""
        SELECT 
            id_pengguna,
            id_produk
        FROM produk_favorit
    """)

    pipe = vk.pipeline(transaction=False)

    for r in rows:

        # user -> produk favorit
        pipe.sadd(
            f"produk_favorit:{r['id_pengguna']}",
            r["id_produk"]
        )

        # reverse index:
        # produk -> user yang favorit
        pipe.sadd(
            f"produk_favorit_user:{r['id_produk']}",
            r["id_pengguna"]
        )

    pipe.execute()

    print(f"  Produk favorit + reverse index: {len(rows)}")


def seed_valkey_ruang_chat():

    print("\n=== Valkey: ruang chat ===")

    rows = fetch_all("""
        SELECT
            id_pengguna,
            id_ruang_chat
        FROM ruang_chat_user
    """)

    pipe = vk.pipeline(transaction=False)

    for r in rows:

        pipe.sadd(
            f"ruang_chat:{r['id_pengguna']}",
            r["id_ruang_chat"]
        )

    pipe.execute()

    print(f"  Ruang chat: {len(rows)}")


def seed_valkey():

    seed_valkey_produk_favorit()

    seed_valkey_ruang_chat()

    print("\nValkey selesai.")



def seed_all():
    seed_pengguna()
    seed_produk()
    seed_pesanan()
    seed_penyewaan()
    seed_pengembalian()
    seed_ruang_chat()
    seed_alamat()
    seed_pembayaran()
    seed_ulasan()
    seed_detail_pesanan()
    seed_pengiriman()
    seed_valkey()


if __name__ == "__main__":
    seed_all()
