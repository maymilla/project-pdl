import time
from pathlib import Path
from scripts.queries.utils.db import koneksi_couchdb, couch_put
from scripts.queries.utils.output import cetak_dan_simpan

OUTPUT_FILE = Path(__file__).resolve().parents[3] / "results" / "dml" / "query_1.txt"

couch = koneksi_couchdb()

def insert_pesanan():

    start = time.perf_counter()

    doc = {
        "_id": "pesanan:test001",
        "type": "pesanan",

        "id_penjual": 1,
        "id_pembeli": 2,
        "id_alamat": 1,

        "tanggal_pesanan": "2026-09-24",

        "status_pesanan": "menunggu_pembayaran",

        "detail_pesanan": [
            {
                "no_urut": 1,
                "id_produk": 10,
                "jenis_transaksi": "beli",
                "harga": 150000
            }
        ],

        "pengiriman": None,
        "id_pembayaran": None
    }


    hasil = couch_put(
        couch,
        doc
    )


    waktu = (
        time.perf_counter()-start
    )*1000


    return waktu, hasil



def main():

    waktu, hasil = insert_pesanan()

    cetak_dan_simpan(
        "QUERY 1 DML\nInsert Pesanan Baru",
        hasil,
        OUTPUT_FILE,
        waktu
    )


if __name__ == "__main__":
    main()