import time
from pathlib import Path

from scripts.queries.utils.db import (
    koneksi_couchdb,
    couch_find,
    couch_get,
    couch_bulk_docs
)

from scripts.queries.utils.output import cetak_dan_simpan


OUTPUT_FILE = (
    Path(__file__).resolve().parents[3]
    / "results"
    / "dml"
    / "query_2.txt"
)


couch = koneksi_couchdb()


def update_produk_terjual():
    start = time.perf_counter()
    pesanan, _ = couch_find(
        couch,
        {
            "type": "pesanan",
            "status_pesanan": "selesai"
        },
        limit=20000
    )
    produk_terjual = set()

    for p in pesanan:
        for d in p.get(
            "detail_pesanan",
            []
        ):
            if d.get(
                "jenis_transaksi"
            ) == "beli":
                
                produk_terjual.add(
                    d["id_produk"]
                )

    docs_update = []

    for pid in produk_terjual:
        produk = couch_get(
            couch,
            f"produk:{pid}"
        )
        if produk:
            produk["status_produk"] = "terjual"
            docs_update.append(
                produk
            )

    hasil_bulk = couch_bulk_docs(
        couch,
        docs_update
    )

    waktu = (
        time.perf_counter()-start
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