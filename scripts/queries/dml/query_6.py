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


def bulk_get(doc_ids):
    if not doc_ids:
        return {}
    body = {"keys": list(doc_ids)}
    resp = session.post(f"{COUCHDB_URL}/_all_docs", params={"include_docs": "true"}, json=body).json()
    hasil = {}
    for row in resp.get("rows", []):
        if "doc" in row and row["doc"] is not None:
            hasil[row["id"]] = row["doc"]
    return hasil


def bulk_write(docs):
    if not docs:
        return []
    body = {"docs": docs}
    return session.post(f"{COUCHDB_URL}/_bulk_docs", json=body).json()


def batalkan_dan_refund():
    waktu = ""
    t0 = time.perf_counter()
    body = {"selector": {"type": "pengiriman", "status_pengiriman": "gagal_kirim"}, "limit": 100000}
    gagal_list = session.post(f"{COUCHDB_URL}/_find", json=body).json().get("docs", [])
    t1 = time.perf_counter()
    print(f"[_find] {len(gagal_list)} docs, {(t1-t0)*1000:.0f} ms")
    waktu += f"[_find] {len(gagal_list)} docs, {(t1-t0)*1000:.0f} ms\n"

    if not gagal_list:
        return []

    id_pesanan_set = {f"pesanan:{pg['id_pesanan']}" for pg in gagal_list}
    pesanan_map = bulk_get(id_pesanan_set)
    t2 = time.perf_counter()
    print(f"[bulk_get pesanan] {len(pesanan_map)} docs, {(t2-t1)*1000:.0f} ms")
    waktu += f"[bulk_get pesanan] {len(pesanan_map)} docs, {(t2-t1)*1000:.0f} ms\n"

    sekarang = datetime.now(timezone.utc).astimezone()
    pesanan_to_update = {}
    id_pembayaran_needed = set()
    hasil_temp = []

    for pg in gagal_list:
        pesanan = pesanan_map.get(f"pesanan:{pg['id_pesanan']}")
        if pesanan is None:
            continue
        if pesanan["status_pesanan"] in ("selesai", "dibatalkan"):
            continue

        tanggal_pesanan = datetime.fromisoformat(pesanan["tanggal_pesanan"])
        if tanggal_pesanan >= sekarang - timedelta(days=BATAS_HARI):
            continue

        pesanan["status_pesanan"] = "dibatalkan"
        pesanan_to_update[pesanan["_id"]] = pesanan
        id_pembayaran_needed.add(f"pembayaran:{pesanan.get("pembayaran", {}).get("id_pembayaran")}")
        hasil_temp.append(pesanan)
    
    t3 = time.perf_counter()
    print(f"[filter loop] {(t3-t2)*1000:.0f} ms")
    waktu += f"[filter loop] {(t3-t2)*1000:.0f} ms\n"

    pembayaran_map = bulk_get(id_pembayaran_needed)
    t4 = time.perf_counter()
    print(f"[bulk_get pembayaran] {len(pembayaran_map)} docs, {(t4-t3)*1000:.0f} ms")
    waktu += f"[bulk_get pembayaran] {len(pembayaran_map)} docs, {(t4-t3)*1000:.0f} ms\n"

    pembayaran_to_update = {}
    hasil = []

    for pesanan in hasil_temp:
        pembayaran = pembayaran_map.get(f"pembayaran:{pesanan.get("pembayaran", {}).get("id_pembayaran")}")
        status_pembayaran_baru = "-"
        if pembayaran is not None and pembayaran["status_pembayaran"] == "berhasil":
            pembayaran["status_pembayaran"] = "refund"
            pembayaran_to_update[pembayaran["_id"]] = pembayaran
            status_pembayaran_baru = "refund"

        hasil.append({
            "id_pesanan": pesanan["id_pesanan"],
            "status_pesanan": "dibatalkan",
            "id_pembayaran": pesanan.get("pembayaran", {}).get("id_pembayaran"),
            "status_pembayaran": status_pembayaran_baru,
        })
        
    t5 = time.perf_counter()
    print(f"[build hasil loop] {(t5-t4)*1000:.0f} ms")
    waktu += f"[build hasil loop] {(t5-t4)*1000:.0f} ms\n"

    bulk_write(list(pesanan_to_update.values()))
    t6 = time.perf_counter()
    print(f"[bulk_write pesanan] {len(pesanan_to_update)} docs, {(t6-t5)*1000:.0f} ms")
    waktu += f"[bulk_write pesanan] {len(pesanan_to_update)} docs, {(t6-t5)*1000:.0f} ms\n"

    bulk_write(list(pembayaran_to_update.values()))
    t7 = time.perf_counter()
    print(f"[bulk_write pembayaran] {len(pembayaran_to_update)} docs, {(t7-t6)*1000:.0f} ms")

    waktu += f"[bulk_write pesanan] {len(pesanan_to_update)} docs, {(t6-t5)*1000:.0f} ms\n"
    return hasil, waktu


if __name__ == "__main__":
    start_time = time.perf_counter()
    data_hasil, waktu_eksekusi = batalkan_dan_refund()
    duration_ms = (time.perf_counter() - start_time) * 1000

    cetak_dan_simpan(
        judul="=== BATALKAN PESANAN + REFUND (GAGAL KIRIM > 7 HARI) ===",
        data=data_hasil,
        output_file="results/dml/query_6.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : CouchDB (bulk read/write)"],
    )
    
    print(waktu_eksekusi)