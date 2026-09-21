import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from valkey import Valkey


ROOT_DIR = Path(__file__).resolve().parents[3]
OUTPUT_FILE = ROOT_DIR / "results" / "read" / "query_8.txt"


def koneksi_valkey():
    return Valkey(
        host=os.getenv("VALKEY_HOST", "127.0.0.1"),
        port=int(os.getenv("VALKEY_PORT", "6379")),
        db=int(os.getenv("VALKEY_DB", "0")),
        decode_responses=True,
    )


def koneksi_couchdb():
    session = requests.Session()
    session.auth = (os.getenv("COUCH_USER"), os.getenv("COUCH_PASSWORD"))
    return session


def ambil_pesanan(couch):
    base_url = os.getenv("COUCH_URL", "http://127.0.0.1:5984").rstrip("/")
    database = os.getenv("COUCH_DB", "gayang")
    response = couch.post(
        f"{base_url}/{database}/_find",
        json={
            "selector": {"type": "pesanan"},
            "fields": ["pembayaran"],
            "limit": 100000,
        },
    )
    response.raise_for_status()
    return response.json().get("docs", [])


def metode_pembayaran_terpopuler(couch, valkey):
    statistik = defaultdict(lambda: {"jumlah_transaksi": 0, "total_nominal": 0})
    pesanan = ambil_pesanan(couch)
    pembayaran_valid = []

    for pesanan_row in pesanan:
        pembayaran = pesanan_row.get("pembayaran")
        if isinstance(pembayaran, dict) and pembayaran.get("id_pembayaran") is not None:
            pembayaran_valid.append(pembayaran)

    pipeline = valkey.pipeline(transaction=False)
    for pembayaran in pembayaran_valid:
        pipeline.get(f"status:pembayaran:{pembayaran['id_pembayaran']}")
    status_pembayaran = pipeline.execute()

    for pembayaran, status in zip(pembayaran_valid, status_pembayaran):
        if status != "berhasil":
            continue
        metode = pembayaran.get("metode_pembayaran", "(tidak diketahui)")
        statistik[metode]["jumlah_transaksi"] += 1
        statistik[metode]["total_nominal"] += pembayaran.get("nominal") or 0

    jumlah_maksimum = max(
        (data["jumlah_transaksi"] for data in statistik.values()),
        default=0,
    )
    hasil = [
        {
            "metode_pembayaran": metode,
            **data,
        }
        for metode, data in statistik.items()
        if data["jumlah_transaksi"] == jumlah_maksimum
    ]
    hasil.sort(key=lambda row: row["metode_pembayaran"])
    return hasil, len(pesanan)


def main():
    load_dotenv(ROOT_DIR / ".env")
    mulai = time.perf_counter()
    hasil, jumlah_pesanan = metode_pembayaran_terpopuler(
        koneksi_couchdb(),
        koneksi_valkey(),
    )
    waktu_ms = (time.perf_counter() - mulai) * 1000

    lines = [
        "=== Query 8: Metode Pembayaran Terpopuler ===",
        f"Waktu jalan  : {datetime.now().isoformat()}",
        f"CouchDB      : {os.getenv('COUCH_URL', 'http://127.0.0.1:5984')}  DB: {os.getenv('COUCH_DB', 'gayang')}",
        f"Valkey       : {os.getenv('VALKEY_HOST', '127.0.0.1')}:{os.getenv('VALKEY_PORT', '6379')}  DB: {os.getenv('VALKEY_DB', '0')}",
        "",
        "=" * 70,
        "HASIL QUERY: METODE PEMBAYARAN PALING SERING DIGUNAKAN",
        "=" * 70,
        f"waktu query  : {waktu_ms:.3f} ms",
        f"pesanan dibaca dari CouchDB : {jumlah_pesanan}",
        f"jumlah hasil : {len(hasil)}",
        "",
    ]

    if hasil:
        for nomor, row in enumerate(hasil, start=1):
            lines.append(
                f"{nomor}. {row['metode_pembayaran']} - "
                f"{row['jumlah_transaksi']} transaksi berhasil - "
                f"total nominal: {row['total_nominal']}"
            )
    else:
        lines.append("Tidak ada transaksi pembayaran berhasil.")

    output = "\n".join(lines)
    print(output)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output + "\n", encoding="utf-8")
    print(f"\n>>> Hasil lengkap tersimpan di: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
