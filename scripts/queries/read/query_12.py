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

def get_semua_riwayat_transaksi_denormalized():
    view_url = f"{COUCHDB_URL}/_design/views/_view/semua_pesanan_riwayat"
    
    hasil_akhir = []
    limit_per_batch = 5000 
    skip = 0

    while True:
        params = {
            "include_docs": "true",
            "descending": "true",
            "limit": limit_per_batch,
            "skip": skip
        }
        
        res = session.get(view_url, params=params).json()
        rows = res.get("rows", [])
        if not rows:
            break

        for row in rows:
            ps = row["doc"]
            
            pembeli = ps.get("pembeli", {})
            pembayaran = ps.get("pembayaran", {})
            pengiriman_list = ps.get("pengiriman") or []
            status_kirim = pengiriman_list[0].get("status_pengiriman") if pengiriman_list else None
            
            for dp in ps.get("detail_pesanan", []):
                hasil_akhir.append({
                    "id_pengguna": pembeli.get("id_pengguna"),
                    "nama": pembeli.get("nama"),
                    "id_pesanan": ps.get("id_pesanan"),
                    "tanggal_pesanan": ps.get("tanggal_pesanan", ""),
                    "nama_produk": dp.get("nama_produk"),
                    "jenis_transaksi": dp.get("jenis_transaksi"),
                    "harga": dp.get("harga"),
                    "status_pesanan": ps.get("status_pesanan"),
                    "status_pembayaran": pembayaran.get("status_pembayaran"),
                    "status_pengiriman": status_kirim,
                    "status_sewa": dp.get("status_sewa"),
                    "status_pengembalian": dp.get("status_pengembalian")
                })
        
        skip += limit_per_batch
        
    hasil_akhir.sort(key=lambda x: str(x["id_pengguna"]))
    return hasil_akhir

if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_semua_riwayat_transaksi_denormalized()

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000
    
    cetak_dan_simpan(
        judul="=== RIWAYAT TRANSAKSI SEMUA PENGGUNA ===",
        data=data_hasil,
        output_file="results/read/query_12.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : Valkey & CouchDB"],
    )