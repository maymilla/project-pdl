from collections import defaultdict
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


def get_top_pengguna_transaksi():
    url = f"{COUCHDB_URL}/_design/views/_view/transaksi_per_user?group=true"
    response = session.get(url).json()
    rows = response.get("rows", [])

    if not rows:
        return []

    user_stats = defaultdict(lambda: [0, 0])

    for row in rows:
        id_pembeli = row["key"][0]
        jenis_transaksi = row["key"][1]
        jumlah = row["value"]

        if jenis_transaksi == "beli":
            user_stats[id_pembeli][0] += jumlah
        elif jenis_transaksi == "sewa":
            user_stats[id_pembeli][1] += jumlah

    rekap_pengguna = []
    for id_pembeli, stats in user_stats.items():
        total = stats[0] + stats[1]
        rekap_pengguna.append({
            "id_pengguna": id_pembeli,
            "jumlah_pembelian": stats[0],
            "jumlah_penyewaan": stats[1],
            "total_transaksi": total,
        })

    rekap_pengguna.sort(key=lambda x: x["total_transaksi"], reverse=True)
    top_10 = rekap_pengguna[:10]

    hasil_akhir = []
    for item in top_10:
        raw_id = str(item["id_pengguna"])
        clean_id = raw_id.replace("pengguna:", "").strip()

        res_user = session.get(f"{COUCHDB_URL}/pengguna:{clean_id}").json()

        if "error" in res_user:
            res_user = session.get(f"{COUCHDB_URL}/{raw_id}").json()

        hasil_akhir.append({
            "id_pengguna": raw_id,
            "nama": res_user.get("nama", "-"),
            "jumlah_pembelian": item["jumlah_pembelian"],
            "jumlah_penyewaan": item["jumlah_penyewaan"],
            "total_transaksi": item["total_transaksi"],
        })

    return hasil_akhir


if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_top_pengguna_transaksi()

    duration_ms = (time.perf_counter() - start_time) * 1000

    cetak_dan_simpan(
        judul="=== LAPORAN TOP PENGGUNA TRANSAKSI ===",
        data=data_hasil,
        output_file="results/read/query_10.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : CouchDB"],
    )