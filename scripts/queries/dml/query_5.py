from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import time
import requests

QUERIES_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = QUERIES_ROOT.parent
PROJECT_ROOT = SCRIPTS_ROOT.parent
for import_root in (QUERIES_ROOT, PROJECT_ROOT):
  if str(import_root) not in sys.path:
    sys.path.append(str(import_root))

from utils.output import cetak_dan_simpan
from scripts.valkey.valkey_access import get_next_id 

COUCHDB_URL = "http://localhost:5984/gayang"
AUTH = ("admin_gayang", "gayang123")

session = requests.Session()
session.auth = AUTH

BATAS_HARI = 3

# fungsi get_next_id() lokal yang lama DIHAPUS


def insert_pengiriman_ulang():
    body = {"selector": {"type": "pengiriman", "status_pengiriman": "gagal_kirim"}, "limit": 1000}
    gagal_list = session.post(f"{COUCHDB_URL}/_find", json=body).json().get("docs", [])

    hasil = []

    for pg in gagal_list:
        pesanan = session.get(f"{COUCHDB_URL}/pesanan:{pg['id_pesanan']}").json()
        if "error" in pesanan:
            continue

        tanggal_pesanan = datetime.fromisoformat(pesanan["tanggal_pesanan"])
        tanggal_kirim = datetime.fromisoformat(pg["tanggal_kirim"])

        if tanggal_kirim > tanggal_pesanan + timedelta(days=BATAS_HARI):
            continue

        entri_terakhir = pesanan["pengiriman"][-1]
        if entri_terakhir["id_pengiriman"] != pg["id_pengiriman"]:
            continue

        id_baru = get_next_id("pengiriman")  
        sekarang = datetime.now(timezone.utc).astimezone().isoformat()

        pengiriman_baru = {
            "_id": f"pengiriman:{id_baru}",
            "type": "pengiriman",
            "id_pengiriman": id_baru,
            "id_pesanan": pg["id_pesanan"],
            "kurir": pg["kurir"],
            "no_resi": None,
            "tanggal_kirim": sekarang,
            "tanggal_terima": None,
            "status_pengiriman": "menunggu",
        }
        session.put(f"{COUCHDB_URL}/pengiriman:{id_baru}", json=pengiriman_baru)

        pesanan["pengiriman"].append(
            {"id_pengiriman": id_baru, "tanggal_kirim": sekarang, "tanggal_terima": None}
        )
        session.put(f"{COUCHDB_URL}/pesanan:{pesanan['id_pesanan']}", json=pesanan)

        hasil.append({
            "id_pesanan": pesanan["id_pesanan"],
            "id_pengiriman_gagal": pg["id_pengiriman"],
            "id_pengiriman_baru": id_baru,
        })

    return hasil


if __name__ == "__main__":
    start_time = time.perf_counter()
    data_hasil = insert_pengiriman_ulang()
    duration_ms = (time.perf_counter() - start_time) * 1000

    cetak_dan_simpan(
        judul="=== INSERT PENGIRIMAN ULANG ===",
        data=data_hasil,
        output_file="results/dml/query_5.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : CouchDB + Valkey (ID counter)"],
    )