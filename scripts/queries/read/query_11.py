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


session = requests.Session()
session.auth = AUTH

def get_produk_tanpa_ulasan():
    url_ulasan = f"{COUCHDB_URL}/_design/views/_view/rating_per_produk?group=true"
    res_ulasan = session.get(url_ulasan).json()
    
    reviewed_ids = set()
    for row in res_ulasan.get("rows", []):
        key = row.get("key")
        if key is not None:
            clean_id = str(key).replace("produk:", "")
            if clean_id.isdigit():
                reviewed_ids.add(int(clean_id))

    url_produk = f"{COUCHDB_URL}/_design/views/_view/produk_by_id?include_docs=true"
    res_produk = session.get(url_produk).json()
    produk_rows = res_produk.get("rows", [])

    all_produk = []
    for row in produk_rows:
        doc = row.get("doc", {})
        raw_id = doc.get("id_produk")
        if raw_id is None and "produk:" in doc.get("_id", ""):
            raw_id = doc["_id"].replace("produk:", "")
            
        if raw_id is not None and str(raw_id).isdigit():
            all_produk.append((int(raw_id), doc))

    all_produk.sort(key=lambda x: x[0])

    hasil = []
    for id_produk_int, doc in all_produk:
        if id_produk_int not in reviewed_ids:
            hasil.append({
                "id_produk": id_produk_int,
                "nama_produk": doc.get("nama_produk"),
                "kondisi": doc.get("kondisi"),
                "harga_jual": doc.get("harga_jual"),
                "harga_sewa": doc.get("harga_sewa"),
                "status_produk": doc.get("status_produk")
            })
        
        if len(hasil) == 10:
            break

    return hasil

if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_produk_tanpa_ulasan()

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000

    cetak_dan_simpan(
        judul="=== LAPORAN PRODUK TANPA ULASAN ===",
        data=data_hasil,
        output_file="results/read/query_11.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : Valkey & CouchDB"],
    )