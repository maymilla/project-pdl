import time
from pathlib import Path
from scripts.queries.utils.db import (koneksi_couchdb, couch_bulk_docs, couch_bulk_get, couch_view_keys)
from scripts.queries.utils.output import cetak_dan_simpan

OUTPUT_FILE = (Path(__file__).resolve().parents[3] / "results" / "dml" / "query_2.txt")

couch = koneksi_couchdb()

def update_produk_terjual():
    start = time.perf_counter()
    produk_terjual = set(
        couch_view_keys(
            couch,
            "views",
            "produk_terjual"
        )
    )

    produk_ids = list(produk_terjual)
    produk_list = couch_bulk_get(
        couch,
        produk_ids
    )

    docs_update = []

    for produk in produk_list:
        produk["status_produk"] = "terjual"
        docs_update.append(
            produk
        )

    hasil_bulk = couch_bulk_docs(
        couch,
        docs_update
    )

    waktu = (
        time.perf_counter() - start
    ) * 1000

    hasil = []

    for r in hasil_bulk:
        if r.get("ok"):
            hasil.append(
                {
                    "id": r["id"],
                    "status": "terjual"
                }
            )

    return waktu, hasil


def main():
    waktu, hasil = update_produk_terjual()
    cetak_dan_simpan(
        "QUERY 2 DML\nUpdate Status Produk Menjadi Terjual",
        hasil,
        OUTPUT_FILE,
        waktu
    )


if __name__ == "__main__":
    main()