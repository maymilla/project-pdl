import time
from pathlib import Path
from scripts.queries.utils.db import koneksi_couchdb, couch_view_keys, couch_put
from scripts.queries.utils.output import cetak_dan_simpan

OUTPUT_FILE = Path(__file__).resolve().parents[3] / "results" / "dml" / "query_4.txt"

couch = koneksi_couchdb()

def insert_ulasan():
    start = time.perf_counter()
    transaksi_beli = couch_view_keys(
        couch,
        "views",
        "transaksi_beli"
    )
    ulasan_existing = set(
        tuple(x)
        for x in couch_view_keys(
            couch,
            "views",
            "ulasan_by_produk_user"
        )
    )

    hasil = None

    for key in transaksi_beli:
        id_produk = key[0]
        id_pengguna = key[1]

        if (id_produk, id_pengguna) not in ulasan_existing:
            doc = {
                "_id": f"ulasan:{id_produk}:{id_pengguna}",
                "type": "ulasan",
                "id_produk": id_produk,
                "id_pengguna": id_pengguna,
                "rating": 5,
                "komentar": (
                    "Produk sesuai dengan "
                    "deskripsi dan kondisinya baik."
                ),
                "tanggal_ulasan": "2026-09-24"
            }

            hasil = couch_put(couch, doc)
            break

    waktu = (
        time.perf_counter() - start
    ) * 1000

    if hasil is None:
        hasil = {
            "error": "tidak ditemukan transaksi valid"
        }

    return waktu, hasil


def main():
    waktu, hasil = insert_ulasan()

    if isinstance(hasil, dict):
        hasil_output = [hasil]
    else:
        hasil_output = [hasil]

    cetak_dan_simpan(
        "QUERY 4 DML\nInsert Ulasan",
        hasil_output,
        OUTPUT_FILE,
        waktu
    )

if __name__ == "__main__":
    main()