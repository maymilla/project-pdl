import requests
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.output import cetak_dan_simpan

COUCHDB_URL = "http://localhost:5984/gayang" 
AUTH = ("admin_gayang", "gayang123") 

def get_metode_pembayaran_teratas():
    url = f"{COUCHDB_URL}/_design/views/_view/stats_by_metode?group=true"
    response = requests.get(url, auth=AUTH).json()
    rows = response.get("rows", [])

    if not rows:
        return []

    max_transaksi = max(row["value"][0] for row in rows)

    hasil = []
    for row in rows:
        count = row["value"][0]
        total_nominal = row["value"][1]
        
        if count == max_transaksi:
            hasil.append({
                "metode_pembayaran": row["key"],
                "jumlah_transaksi_berhasil": count,
                "total_nominal": total_nominal
            })

    return hasil

if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_metode_pembayaran_teratas()

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000

    cetak_dan_simpan(
        judul="=== LAPORAN METODE PEMBAYARAN ===",
        data=data_hasil,
        output_file="results/read/query_8.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : Valkey & CouchDB"],
    )
