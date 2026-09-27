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
from scripts.valkey.valkey_access import reserve_id_block

COUCHDB_URL = "http://localhost:5984/gayang"
AUTH = ("admin_gayang", "gayang123")

session = requests.Session()
session.auth = AUTH

BATAS_HARI = 3


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

def insert_pengiriman_ulang():
    rincian_waktu = []
    t0 = time.perf_counter()
    body = {"selector": {"type": "pengiriman", "status_pengiriman": "gagal_kirim"}, "limit": 100000}
    gagal_list = session.post(f"{COUCHDB_URL}/_find", json=body).json().get("docs", [])
    t1 = time.perf_counter()
    rincian_waktu.append(("[_find]", len(gagal_list), (t1 - t0) * 1000))

    if not gagal_list:
        return [], rincian_waktu

    id_pesanan_set = {f"pesanan:{pg['id_pesanan']}" for pg in gagal_list}
    pesanan_map = bulk_get(id_pesanan_set)
    t2 = time.perf_counter()
    rincian_waktu.append(("[bulk_get pesanan]", len(pesanan_map), (t2 - t1) * 1000))

    # PASS 1: filter dulu, kumpulin yang qualify TANPA generate ID
    kandidat = []
    pesanan_yang_berubah = {}

    for pg in gagal_list:
        pesanan = pesanan_map.get(f"pesanan:{pg['id_pesanan']}")
        if pesanan is None:
            continue

        tanggal_pesanan = datetime.fromisoformat(pesanan["tanggal_pesanan"])
        tanggal_kirim = datetime.fromisoformat(pg["tanggal_kirim"])
        if tanggal_kirim > tanggal_pesanan + timedelta(days=BATAS_HARI):
            continue

        pesanan_current = pesanan_yang_berubah.get(pesanan["_id"], pesanan)
        entri_terakhir = pesanan_current["pengiriman"][-1]
        if entri_terakhir["id_pengiriman"] != pg["id_pengiriman"]:
            continue

        pesanan_yang_berubah[pesanan["_id"]] = pesanan_current
        kandidat.append((pg, pesanan_current))

    t3 = time.perf_counter()
    rincian_waktu.append(("[filter loop]", None, (t3 - t2) * 1000))

    if not kandidat:
        return [], rincian_waktu

    # PASS 2: reserve SEMUA ID sekaligus (1 round-trip ke Valkey, bukan N kali)
    id_awal = reserve_id_block("pengiriman", len(kandidat))
    t4 = time.perf_counter()
    rincian_waktu.append(("[reserve_id_block]", len(kandidat), (t4 - t3) * 1000))
    sekarang = datetime.now(timezone.utc).astimezone().isoformat()

    pengiriman_baru_list = []
    hasil = []

    for i, (pg, pesanan_current) in enumerate(kandidat):
        id_baru = id_awal + i

        pengiriman_baru_list.append({
            "_id": f"pengiriman:{id_baru}",
            "type": "pengiriman",
            "id_pengiriman": id_baru,
            "id_pesanan": pg["id_pesanan"],
            "kurir": pg["kurir"],
            "no_resi": None,
            "tanggal_kirim": sekarang,
            "tanggal_terima": None,
            "status_pengiriman": "menunggu",
        })

        pesanan_current["pengiriman"].append(
            {"id_pengiriman": id_baru, "tanggal_kirim": sekarang, "tanggal_terima": None}
        )

        hasil.append({
            "id_pesanan": pesanan_current["id_pesanan"],
            "id_pengiriman_gagal": pg["id_pengiriman"],
            "id_pengiriman_baru": id_baru,
        })

    t5 = time.perf_counter()
    rincian_waktu.append(("[build loop]", None, (t5 - t4) * 1000))

    bulk_write(pengiriman_baru_list)
    t6 = time.perf_counter()
    rincian_waktu.append(("[bulk_write pengiriman]", len(pengiriman_baru_list), (t6 - t5) * 1000))

    bulk_write(list(pesanan_yang_berubah.values()))
    t7 = time.perf_counter()
    rincian_waktu.append(("[bulk_write pesanan]", len(pesanan_yang_berubah), (t7 - t6) * 1000))

    return hasil, rincian_waktu

# def insert_pengiriman_ulang():
#     t0 = time.perf_counter()
#     body = {"selector": {"type": "pengiriman", "status_pengiriman": "gagal_kirim"}, "limit": 100000}
#     gagal_list = session.post(f"{COUCHDB_URL}/_find", json=body).json().get("docs", [])
#     t1 = time.perf_counter()
#     print(f"[_find] {len(gagal_list)} docs, {(t1-t0)*1000:.0f} ms")
    
#     if not gagal_list:
#         return []

#     id_pesanan_set = {f"pesanan:{pg['id_pesanan']}" for pg in gagal_list}
#     pesanan_map = bulk_get(id_pesanan_set)  # dict: "pesanan:X" -> doc
#     t2 = time.perf_counter()
#     print(f"[bulk_get pesanan] {len(pesanan_map)} docs, {(t2-t1)*1000:.0f} ms")

#     pengiriman_baru_list = []
#     pesanan_yang_berubah = {}  
#     hasil = []
    
#     for pg in gagal_list:
#         pesanan = pesanan_map.get(f"pesanan:{pg['id_pesanan']}")
#         if pesanan is None:
#             continue

#         tanggal_pesanan = datetime.fromisoformat(pesanan["tanggal_pesanan"])
#         tanggal_kirim = datetime.fromisoformat(pg["tanggal_kirim"])

#         if tanggal_kirim > tanggal_pesanan + timedelta(days=BATAS_HARI):
#             continue

#         pesanan_current = pesanan_yang_berubah.get(pesanan["_id"], pesanan)

#         entri_terakhir = pesanan_current["pengiriman"][-1]
#         if entri_terakhir["id_pengiriman"] != pg["id_pengiriman"]:
#             continue

#         t_getid_total = 0
#         t_a = time.perf_counter()
#         id_baru = get_next_id("pengiriman")  
#         t_getid_total += time.perf_counter() - t_a
#         print(f"[get_next_id total, {t_getid_total*1000:.0f} ms")
        
#         sekarang = datetime.now(timezone.utc).astimezone().isoformat()

#         pengiriman_baru_list.append({
#             "_id": f"pengiriman:{id_baru}",
#             "type": "pengiriman",
#             "id_pengiriman": id_baru,
#             "id_pesanan": pg["id_pesanan"],
#             "kurir": pg["kurir"],
#             "no_resi": None,
#             "tanggal_kirim": sekarang,
#             "tanggal_terima": None,
#             "status_pengiriman": "menunggu",
#         })

#         pesanan_current["pengiriman"].append(
#             {"id_pengiriman": id_baru, "tanggal_kirim": sekarang, "tanggal_terima": None}
#         )
#         pesanan_yang_berubah[pesanan["_id"]] = pesanan_current

#         hasil.append({
#             "id_pesanan": pesanan["id_pesanan"],
#             "id_pengiriman_gagal": pg["id_pengiriman"],
#             "id_pengiriman_baru": id_baru,
#         })
        
#     t3 = time.perf_counter()
#     print(f"[loop processing] {(t3-t2)*1000:.0f} ms")


#     bulk_write(pengiriman_baru_list)
#     t4 = time.perf_counter()
#     print(f"[bulk_write pengiriman] {len(pengiriman_baru_list)} docs, {(t4-t3)*1000:.0f} ms")

#     bulk_write(list(pesanan_yang_berubah.values()))
#     t5 = time.perf_counter()
#     print(f"[bulk_write pesanan] {len(pesanan_yang_berubah)} docs, {(t5-t4)*1000:.0f} ms")


#     return hasil


if __name__ == "__main__":
    start_time = time.perf_counter()
    data_hasil, rincian_waktu = insert_pengiriman_ulang()
    duration_ms = (time.perf_counter() - start_time) * 1000

    cetak_dan_simpan(
        judul="=== INSERT PENGIRIMAN ULANG (GAGAL KIRIM ≤ 3 HARI) ===",
        data=data_hasil,
        output_file="results/dml/query_5.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : CouchDB + Valkey (bulk read/write)"],
    )

    print("Rincian Waktu Eksekusi:")
    for tahap, jumlah, waktu_ms in rincian_waktu:
        detail_jumlah = f" {jumlah} docs/ids," if jumlah is not None else ""
        print(f"{tahap}{detail_jumlah} {waktu_ms:.0f} ms")