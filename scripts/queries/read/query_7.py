import os
from pathlib import Path
import sys
import time
import requests
from valkey import Valkey

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.output import cetak_dan_simpan

VALKEY_HOST = os.getenv("VALKEY_HOST", "127.0.0.1")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
VALKEY_DB = int(os.getenv("VALKEY_DB", "0"))

COUCHDB_URL = "http://localhost:5984/gayang"
AUTH = ("admin_gayang", "gayang123")

vk = Valkey(
    host=VALKEY_HOST,
    port=VALKEY_PORT,
    db=VALKEY_DB,
    decode_responses=True,
)

session = requests.Session()
session.auth = AUTH


def get_top_produk_favorit_detail():
    keys = vk.keys("produk_favorit_user:*")
    if not keys:
        return []

    pipe = vk.pipeline(transaction=False)
    for k in keys:
        pipe.scard(k)
    counts = pipe.execute()

    favorit_counts = {
        key.replace("produk_favorit_user:", ""): count
        for key, count in zip(keys, counts)
    }

    max_favorit = max(favorit_counts.values()) if favorit_counts else 0
    top_produk_ids = [
        id_p for id_p, count in favorit_counts.items() if count == max_favorit
    ]

    hasil = []
    for id_p in top_produk_ids:
        r_p = session.get(f"{COUCHDB_URL}/produk:{id_p}").json()
        if "error" in r_p:
            r_p = session.get(f"{COUCHDB_URL}/{id_p}").json()

        nama_produk = r_p.get("nama_produk", "-")
        id_penjual = r_p.get("id_penjual")

        nama_penjual = "-"
        if id_penjual:
            clean_id = str(id_penjual).replace("pengguna:", "")
            r_pe = session.get(f"{COUCHDB_URL}/pengguna:{clean_id}").json()
            nama_penjual = r_pe.get("nama", "-")

        hasil.append({
            "nama_produk": nama_produk,
            "nama_penjual": nama_penjual,
            "jumlah_favorit": max_favorit,
        })

    return hasil


if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_top_produk_favorit_detail()

    duration_ms = (time.perf_counter() - start_time) * 1000

    cetak_dan_simpan(
        judul="=== LAPORAN PRODUK FAVORIT TERBANYAK ===",
        data=data_hasil,
        output_file="results/read/query_7.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : Valkey & CouchDB"],
    )