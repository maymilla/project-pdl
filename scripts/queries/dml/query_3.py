import time
from pathlib import Path
from scripts.queries.utils.db import koneksi_valkey, koneksi_couchdb, couch_find
from scripts.queries.utils.output import cetak_dan_simpan

OUTPUT_FILE = Path(__file__).resolve().parents[3] / "results" / "dml" / "query_3.txt"

vk = koneksi_valkey()
couch = koneksi_couchdb()

def delete_produk_favorit():
    start = time.perf_counter()
    produk, _ = couch_find(
        couch,
        {
            "type": "produk",
            "status_produk": {
                "$in": [
                    "nonaktif",
                    "terjual"
                ]
            }
        },
        limit=20000
    )

    jumlah = 0

    for p in produk:

        pid = str(p["id_produk"])
        users = vk.smembers(
            f"produk_favorit_user:{pid}"
        )

        for uid in users:
            deleted = vk.srem(
                f"produk_favorit:{uid}",
                pid
            )

            jumlah += deleted

        vk.delete(
            f"produk_favorit_user:{pid}"
        )

    waktu = (
        time.perf_counter() - start
    ) * 1000

    return waktu, [jumlah]


def main():
    waktu, hasil = delete_produk_favorit()

    cetak_dan_simpan(
        "QUERY 3 DML\nDelete Produk Favorit",
        [
            {
                "jumlah_deleted": hasil
            }
        ],
        OUTPUT_FILE,
        waktu
    )


if __name__=="__main__":
    main()