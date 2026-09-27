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

def get_semua_riwayat_transaksi():
    view_url = f"{COUCHDB_URL}/_design/views/_view/semua_pesanan_riwayat"
    
    hasil_akhir = []
    user_cache = {}
    produk_cache = {}
    pembayaran_cache = {}

    limit_per_batch = 5000  
    skip = 0
    total_diproses = 0
    
    print("Memulai pengambilan data riwayat transaksi via View...")

    while True:
        params = {
            "include_docs": "true",
            "descending": "true", 
            "limit": limit_per_batch,
            "skip": skip
        }
        
        res = session.get(view_url, params=params).json()
        
        if "error" in res:
            print(f"Error CouchDB: {res}")
            break
            
        rows = res.get("rows", [])
        if not rows:
            break  

        pesanan_batch = [row["doc"] for row in rows if "doc" in row]

        for ps in pesanan_batch:
            id_pesanan = ps.get("_id")
            id_pembeli = ps.get("id_pembeli")
            
            if id_pembeli not in user_cache:
                user_key = id_pembeli if str(id_pembeli).startswith("pengguna:") else f"pengguna:{id_pembeli}"
                res_user = session.get(f"{COUCHDB_URL}/{user_key}").json()
                user_cache[id_pembeli] = res_user.get("nama", "Unknown")
            nama_user = user_cache[id_pembeli]

            id_pembayaran = ps.get("id_pembayaran")
            if id_pembayaran and id_pembayaran not in pembayaran_cache:
                res_pb = session.get(f"{COUCHDB_URL}/pembayaran:{id_pembayaran}").json()
                pembayaran_cache[id_pembayaran] = res_pb.get("status_pembayaran")
            status_pembayaran = pembayaran_cache.get(id_pembayaran) if id_pembayaran else None

            pengiriman_list = ps.get("pengiriman") or []
            status_kirim = pengiriman_list[0].get("status_pengiriman") if pengiriman_list else None

            details = ps.get("detail_pesanan") or []
            
            for dp in details:
                id_produk = dp.get("id_produk")
                if id_produk and id_produk not in produk_cache:
                    res_prod = session.get(f"{COUCHDB_URL}/produk:{id_produk}").json()
                    produk_cache[id_produk] = res_prod.get("nama_produk")
                nama_produk = produk_cache.get(id_produk)

                status_sewa = dp.get("status_sewa") 
                status_pengembalian = dp.get("status_pengembalian")

                hasil_akhir.append({
                    "id_pengguna": id_pembeli,
                    "nama": nama_user,
                    "id_pesanan": id_pesanan,
                    "tanggal_pesanan": ps.get("tanggal_pesanan", ""),
                    "nama_produk": nama_produk,
                    "jenis_transaksi": dp.get("jenis_transaksi"),
                    "harga": dp.get("harga"),
                    "status_pesanan": ps.get("status_pesanan"),
                    "status_pembayaran": status_pembayaran,
                    "status_pengiriman": status_kirim,
                    "status_sewa": status_sewa,
                    "status_pengembalian": status_pengembalian
                })
        
        total_diproses += len(pesanan_batch)
        print(f"-> Berhasil memproses {total_diproses} dokumen...")
        
        skip += limit_per_batch 
     
        if total_diproses >= 5000: 
             break

    hasil_akhir.sort(key=lambda x: str(x["id_pengguna"]))

    return hasil_akhir

if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_semua_riwayat_transaksi()

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000
    
    cetak_dan_simpan(
        judul="=== RIWAYAT TRANSAKSI SEMUA PENGGUNA ===",
        data=data_hasil,
        output_file="results/read/query_12.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : Valkey & CouchDB"],
    )