from datetime import datetime
import os
from pathlib import Path
import time
import requests
from valkey import Valkey

import sys
from pathlib import Path

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


def simpan_dan_print(judul, meta_lines, hasil_lines, output_file: Path):
    lines = [judul, f"Waktu jalan   : {datetime.now().isoformat()}"]
    lines += meta_lines
    lines += ["", "=" * 75]
    lines += hasil_lines
    output = "\n".join(lines)
    print(output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(output + "\n", encoding="utf-8")
    print(f"\n>>> Hasil lengkap tersimpan di: {output_file}")
    return output


def get_top_produk_favorit_detail():
    keys = vk.keys("produk_favorit_user:*")
    favorit_counts = {}
    for key in keys:
        id_produk = key.replace("produk_favorit_user:", "")
        count = vk.scard(key)
        favorit_counts[id_produk] = count

    if not favorit_counts:
        return []

    max_favorit = max(favorit_counts.values())
    top_produk_ids = [
        id_p for id_p, count in favorit_counts.items() if count == max_favorit
    ]

    hasil = []
    for id_p in top_produk_ids:
        # Ambil dokumen produk dari CouchDB
        res_p = requests.get(f"{COUCHDB_URL}/produk:{id_p}", auth=AUTH).json()
        if "error" in res_p:
            res_p = requests.get(f"{COUCHDB_URL}/{id_p}", auth=AUTH).json()

        nama_produk = res_p.get("nama_produk", "-")
        id_penjual = res_p.get("id_penjual")

        # Ambil nama penjual
        nama_penjual = "-"
        if id_penjual:
            clean_penjual_id = str(id_penjual).replace("pengguna:", "")
            res_pe = requests.get(
                f"{COUCHDB_URL}/pengguna:{clean_penjual_id}", auth=AUTH
            ).json()
            nama_penjual = res_pe.get("nama", "-")

        hasil.append({
            "nama_produk": nama_produk,
            "nama_penjual": nama_penjual,
            "jumlah_favorit": max_favorit,
        })

    return hasil


if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_top_produk_favorit_detail()

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000

    cetak_dan_simpan(
        judul="=== LAPORAN PRODUK FAVORIT TERBANYAK ===",
        data=data_hasil,
        output_file="results/read/query_7.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : Valkey & CouchDB"],
    )