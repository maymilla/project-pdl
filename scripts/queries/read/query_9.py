import requests
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.output import cetak_dan_simpan

COUCHDB_URL = "http://localhost:5984/gayang" 
AUTH = ("admin_gayang", "gayang123")                        # ganti password

session = requests.Session()
session.auth = AUTH

def get_top_rating():
    url = f"{COUCHDB_URL}/_design/views/_view/rating_per_produk"
    
    res_global = session.get(f"{url}?group=false").json()
    stats_g = res_global["rows"][0]["value"]
    avg_global = stats_g["sum"] / stats_g["count"]

    res_produk = session.get(f"{url}?group=true").json()
    
    hasil = []
    for row in res_produk.get("rows", []):
        id_prod = row["key"]
        count = row["value"]["count"]
        avg_prod = row["value"]["sum"] / count
        
        if avg_prod > avg_global:
            hasil.append({
                "id_produk": id_prod,
                "jumlah_ulasan": count,
                "rata_rata_rating": round(avg_prod, 2)
            })

    hasil.sort(key=lambda x: x["rata_rata_rating"], reverse=True)
    return hasil[:10]

if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_top_rating()

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000

    cetak_dan_simpan(
        judul="=== LAPORAN TOP RATING ===",
        data=data_hasil,
        output_file="results/read/query_9.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : Valkey & CouchDB"],
    )