from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import time
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.output import cetak_dan_simpan

COUCHDB_URL = "http://localhost:5984/gayang"
AUTH = ("admin_gayang", "gayang123")

session = requests.Session()
session.auth = AUTH

BATAS_HARI = 7


def batalkan_dan_refund():
    body = {"selector": {"type": "pengiriman", "status_pengiriman": "gagal_kirim"}, "limit": 1000}
    gagal_list = session.post(f"{COUCHDB_URL}/_find", json=body).json().get("docs", [])

    sekarang = datetime.now(timezone.utc).astimezone()
    hasil = []

    for pg in gagal_list:
        pesanan = session.get(f"{COUCHDB_URL}/pesanan:{pg['id_pesanan']}").json()
        if "error" in pesanan:
            continue
        if pesanan["status_pesanan"] in ("selesai", "dibatalkan"):
            continue

        tanggal_pesanan = datetime.fromisoformat(pesanan["tanggal_pesanan"])
        if tanggal_pesanan >= sekarang - timedelta(days=BATAS_HARI):
            continue

        pesanan["status_pesanan"] = "dibatalkan"
        session.put(f"{COUCHDB_URL}/pesanan:{pesanan['id_pesanan']}", json=pesanan)

        status_pembayaran_baru = "-"
        pembayaran = session.get(f"{COUCHDB_URL}/pembayaran:{pesanan['id_pembayaran']}").json()
        if "error" not in pembayaran and pembayaran["status_pembayaran"] == "berhasil":
            pembayaran["status_pembayaran"] = "refund"
            session.put(f"{COUCHDB_URL}/pembayaran:{pembayaran['id_pembayaran']}", json=pembayaran)
            status_pembayaran_baru = "refund"

        hasil.append({
            "id_pesanan": pesanan["id_pesanan"],
            "status_pesanan": "dibatalkan",
            "id_pembayaran": pesanan["id_pembayaran"],
            "status_pembayaran": status_pembayaran_baru,
        })

    return hasil


if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = batalkan_dan_refund()

    duration_ms = (time.perf_counter() - start_time) * 1000

    cetak_dan_simpan(
        judul="=== BATALKAN PESANAN + REFUND (GAGAL KIRIM > 7 HARI) ===",
        data=data_hasil,
        output_file="results/dml/query_6.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : CouchDB"],
    )