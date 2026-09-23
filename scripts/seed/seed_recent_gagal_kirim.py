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

BASE_ID = 9_000_000


def buat_pesanan_gagal_kirim(n, id_penjual=7317, id_pembeli=8307, id_alamat=4467):
    dibuat = []

    for i in range(n):
        id_pesanan = BASE_ID + i
        id_pengiriman = BASE_ID + i
        id_pembayaran = BASE_ID + i

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
            print(f"  {doc['_id']} sudah ada, lewati (jalankan ulang aman).")
            continue

        r.raise_for_status()

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
    print("Sekarang jalankan scripts/queries/dml_5_8.py -- query 5 seharusnya menemukan kandidat ini.")


if __name__ == "__main__":
    main()
