"""
seed_recent_gagal_kirim.py

Menambahkan beberapa dokumen pesanan BARU langsung ke CouchDB + Valkey,
dengan tanggal_pesanan dalam 3 hari terakhir dan status_pengiriman =
"gagal_kirim", supaya query 5 & 6 (di dml_5_8.py) punya target nyata
untuk diuji.

Ini TIDAK menyentuh PostgreSQL -- dokumen dibuat langsung di CouchDB
dan status-nya langsung di-set di Valkey, meniru hasil seed_nosql.py.

Cara pakai:
    python seed_recent_gagal_kirim.py

Jalankan SEBELUM dml_5_8.py.
"""

import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from valkey import Valkey


load_dotenv()

COUCH_URL = os.getenv("COUCH_URL", "http://127.0.0.1:5984").rstrip("/")
COUCH_DB = os.getenv("COUCH_DB", "gayang")
COUCH_USER = os.getenv("COUCH_USER")
COUCH_PASSWORD = os.getenv("COUCH_PASSWORD")

VALKEY_HOST = os.getenv("VALKEY_HOST", "127.0.0.1")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
VALKEY_DB = int(os.getenv("VALKEY_DB", "0"))

couch = requests.Session()
couch.auth = (COUCH_USER, COUCH_PASSWORD)

vk = Valkey(
    host=VALKEY_HOST,
    port=VALKEY_PORT,
    db=VALKEY_DB,
    decode_responses=True,
)

# ID awal untuk dokumen buatan -- dipilih besar supaya tidak
# bentrok dengan id_pesanan/id_pengiriman/id_pembayaran hasil seeding asli.
BASE_ID = 9_000_000


def buat_pesanan_gagal_kirim(n, id_penjual=7317, id_pembeli=8307, id_alamat=4467):
    """
    Membuat n dokumen pesanan baru:
      - tanggal_pesanan tersebar dalam 0-2 hari terakhir (masih dalam
        jendela "maksimal 3 hari" yang diminta query 5)
      - status_pesanan   = menunggu_pembayaran (Valkey)
      - status_pembayaran = pending (Valkey)
      - status_pengiriman = gagal_kirim (Valkey)  <- target utama
      - belum ada percobaan pengiriman ke-2 (belum retry)
    """
    dibuat = []

    for i in range(n):
        id_pesanan = BASE_ID + i
        id_pengiriman = BASE_ID + i
        id_pembayaran = BASE_ID + i

        # sebar tanggal: 0, 12, 24, ... jam ke belakang dari sekarang
        jam_mundur = i * 8
        tanggal_pesanan = (datetime.utcnow() - timedelta(hours=jam_mundur)).isoformat()

        doc = {
            "_id": f"pesanan:{id_pesanan}",
            "type": "pesanan",
            "id_pesanan": id_pesanan,
            "id_penjual": id_penjual,
            "id_pembeli": id_pembeli,
            "id_alamat": id_alamat,
            "tanggal_pesanan": tanggal_pesanan,
            "total_pesanan": 150000,
            "pembayaran": {
                "id_pembayaran": id_pembayaran,
                "metode_pembayaran": "Virtual Account",
                "no_referensi": f"PAY-test-{id_pesanan}",
                "nominal": 150000,
                "waktu_pembayaran": None,
                "bukti_pembayaran": None,
            },
            "pengiriman": [
                {
                    "id_pengiriman": id_pengiriman,
                    "kurir": "JNE",
                    "no_resi": None,
                    "tanggal_kirim": tanggal_pesanan,
                    "tanggal_terima": None,
                }
            ],
            "detail_pesanan": [
                {
                    "id_detail": id_pesanan,
                    "no_urut": 1,
                    "id_produk": 1,
                    "jenis_transaksi": "beli",
                    "harga": 150000,
                }
            ],
        }

        r = couch.put(f"{COUCH_URL}/{COUCH_DB}/{doc['_id']}", json=doc)

        if r.status_code == 409:
            # dokumen dengan _id ini sudah ada dari run sebelumnya -> lewati
            print(f"  {doc['_id']} sudah ada, lewati (jalankan ulang aman).")
            continue

        r.raise_for_status()

        # set status di Valkey (meniru p1_denorm.valkey_status_export)
        vk.set(f"status:pesanan:{id_pesanan}", "menunggu_pembayaran")
        vk.set(f"status:pembayaran:{id_pembayaran}", "pending")
        vk.set(f"status:pengiriman:{id_pengiriman}", "gagal_kirim")

        dibuat.append(doc["_id"])
        print(f"  dibuat {doc['_id']}  tanggal_pesanan={tanggal_pesanan}  "
              f"status:pengiriman:{id_pengiriman}=gagal_kirim")

    return dibuat


def main():
    print("=== Seeding pesanan gagal_kirim (3 hari terakhir) ===\n")
    dibuat = buat_pesanan_gagal_kirim(n=5)

    print(f"\nTotal dokumen baru dibuat: {len(dibuat)}")
    print("Sekarang jalankan dml_5_8.py -- query 5 seharusnya menemukan kandidat ini.")


if __name__ == "__main__":
    main()
