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

def get_riwayat_transaksi_pengguna(id_pembeli=1):
    docs = []
    for target_id in [int(id_pembeli), str(id_pembeli), f"pengguna:{id_pembeli}"]:
        payload = {
            "selector": {
                "type": "pesanan",
                "id_pembeli": target_id
            }
        }
        res = requests.post(f"{COUCHDB_URL}/_find", json=payload, auth=AUTH).json()
        docs = res.get("docs", [])
        if docs:
            break

    if not docs:
        print("Data pesanan tidak ditemukan di CouchDB.")
        return []

    docs.sort(key=lambda x: x.get("tanggal_pesanan", ""), reverse=True)

    res_user = requests.get(f"{COUCHDB_URL}/pengguna:{id_pembeli}", auth=AUTH).json()
    nama_user = res_user.get("nama", "Unknown")

    hasil_akhir = []
    for ps in docs:
        id_pesanan = ps["_id"]
        details = ps.get("detail_pesanan") or []
        pengiriman_list = ps.get("pengiriman") or []
        status_kirim = pengiriman_list[0].get("status_pengiriman") if pengiriman_list else None

        id_pembayaran = ps.get("id_pembayaran")
        pb_doc = requests.get(f"{COUCHDB_URL}/pembayaran:{id_pembayaran}", auth=AUTH).json() if id_pembayaran else {}

        for dp in details:
            id_produk = dp.get("id_produk")
            prod_doc = requests.get(f"{COUCHDB_URL}/produk:{id_produk}", auth=AUTH).json() if id_produk else {}

            hasil_akhir.append({
                "nama": nama_user,
                "id_pesanan": id_pesanan,
                "tanggal_pesanan": ps.get("tanggal_pesanan"),
                "nama_produk": prod_doc.get("nama_produk"),
                "jenis_transaksi": dp.get("jenis_transaksi"),
                "harga": dp.get("harga"),
                "status_pesanan": ps.get("status_pesanan"),
                "status_pembayaran": pb_doc.get("status_pembayaran"),
                "status_pengiriman": status_kirim
            })

    return hasil_akhir

if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = get_riwayat_transaksi_pengguna(1)

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000

    cetak_dan_simpan(
        judul="=== RIWAYAT TRANSAKSI PENGGUNA ===",
        data=data_hasil,
        output_file="results/read/query_12.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : Valkey & CouchDB"],
    )