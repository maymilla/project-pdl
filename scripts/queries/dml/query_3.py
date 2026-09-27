import time
from pathlib import Path
from scripts.queries.utils.db import koneksi_valkey, koneksi_couchdb, couch_view_keys
from scripts.queries.utils.output import cetak_dan_simpan

OUTPUT_FILE = Path(__file__).resolve().parents[3] / "results" / "dml" / "query_3.txt"

vk = koneksi_valkey()
couch = koneksi_couchdb()

def delete_produk_favorit():
    start = time.perf_counter()
    produk_ids = couch_view_keys(
        couch,
        "views",
        "produk_nonaktif_terjual"
    )
    jumlah = 0
    
    for pid in produk_ids:
        pid = str(pid)
        users = vk.smembers(
            f"produk_favorit_user:{pid}"
        )
        if not users:
            vk.delete(
                f"produk_favorit_user:{pid}"
            )
            continue
        pipe = vk.pipeline()
        for uid in users:
            pipe.srem(
                f"produk_favorit:{uid}",
                pid
            )

        pipe.delete(
            f"produk_favorit_user:{pid}"
        )

        hasil = pipe.execute()
        for r in hasil[:-1]:
            jumlah += r

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