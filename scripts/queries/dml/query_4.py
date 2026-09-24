import time
from pathlib import Path

from scripts.queries.utils.db import (
    koneksi_couchdb,
    couch_find,
    couch_put
)

from scripts.queries.utils.output import cetak_dan_simpan

OUTPUT_FILE = Path(__file__).resolve().parents[3] / "results" / "dml" / "query_4.txt"

couch = koneksi_couchdb()

def insert_ulasan():
    start = time.perf_counter()

    pesanan, _ = couch_find(
        couch,
        {
            "type": "pesanan",
            "status_pesanan": "selesai"
        },
        limit=20000
    )
    hasil = None

    for p in pesanan:
        for d in p.get("detail_pesanan", []):
            if d.get("jenis_transaksi") == "beli":

                id_produk = d["id_produk"]
                id_pengguna = p["id_pembeli"]

                ulasan, _ = couch_find(
                    couch,
                    {
                        "type": "ulasan",
                        "id_produk": id_produk,
                        "id_pengguna": id_pengguna
                    },
                    limit=1
                )
                if len(ulasan) == 0:
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
                    hasil = couch_put(
                        couch,
                        doc
                    )
                    break
        if hasil:
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