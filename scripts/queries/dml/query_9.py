import argparse
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from valkey import Valkey


ROOT_DIR = Path(__file__).resolve().parents[3]
OUTPUT_FILE = ROOT_DIR / "results" / "dml" / "query_9.txt"


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


def couch_find(couch, selector, fields=None, limit=1000):
    base_url = os.getenv("COUCH_URL", "http://127.0.0.1:5984").rstrip("/")
    database = os.getenv("COUCH_DB", "gayang")
    body = {"selector": selector, "limit": limit}
    if fields:
        body["fields"] = fields
    start = time.perf_counter()
    response = couch.post(f"{base_url}/{database}/_find", json=body)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.raise_for_status()
    return response.json().get("docs", []), elapsed_ms


def batalkan_pesanan_lewat_batas_pembayaran(couch, valkey, batas_jam=24, eksekusi_tulis=True):
    batas_waktu = (datetime.utcnow() - timedelta(hours=batas_jam)).isoformat()

    kandidat, elapsed_ms = couch_find(
        couch,
        {"type": "pesanan", "tanggal_pesanan": {"$lt": batas_waktu}},
        fields=["_id", "tanggal_pesanan", "pembayaran"],
        limit=100000,
    )

    dibatalkan = []
    for doc in kandidat:
        id_pesanan = doc["_id"].split(":")[1]

        status_pesanan = valkey.get(f"status:pesanan:{id_pesanan}")
        if status_pesanan != "menunggu_pembayaran":
            continue

        pembayaran = doc.get("pembayaran") or {}
        id_pembayaran = pembayaran.get("id_pembayaran")
        status_pembayaran = valkey.get(f"status:pembayaran:{id_pembayaran}") if id_pembayaran else None

        if status_pembayaran == "berhasil":
            continue

        if eksekusi_tulis:
            valkey.set(f"status:pesanan:{id_pesanan}", "dibatalkan")

        dibatalkan.append(id_pesanan)

    return dibatalkan, len(kandidat), elapsed_ms


def main():
    parser = argparse.ArgumentParser(
        description="Query 9 (DML NoSQL): batalkan pesanan yang melewati batas pembayaran."
    )
    parser.add_argument("--batas-jam", type=int, default=24, help="Batas jam sejak pesanan dibuat (default: 24)")
    parser.add_argument("--dry-run", action="store_true", help="Hanya tampilkan kandidat tanpa menulis ke Valkey")
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    couch = koneksi_couchdb()
    valkey = koneksi_valkey()

    mulai = time.perf_counter()
    dibatalkan, jumlah_kandidat, elapsed_ms = batalkan_pesanan_lewat_batas_pembayaran(
        couch, valkey, args.batas_jam, eksekusi_tulis=not args.dry_run
    )
    waktu_ms = (time.perf_counter() - mulai) * 1000

    lines = [
        "=== Query 9 (DML): Batalkan Pesanan Lewat Batas Pembayaran (NoSQL) ===",
        f"Waktu jalan  : {datetime.now().isoformat()}",
        f"CouchDB      : {os.getenv('COUCH_URL', 'http://127.0.0.1:5984')}  DB: {os.getenv('COUCH_DB', 'gayang')}",
        f"Valkey       : {os.getenv('VALKEY_HOST', '127.0.0.1')}:{os.getenv('VALKEY_PORT', '6379')}  DB: {os.getenv('VALKEY_DB', '0')}",
        f"mode         : {'DRY-RUN (tanpa tulis)' if args.dry_run else 'EKSEKUSI (tulis ke Valkey)'}",
        "",
        "=" * 70,
        "HASIL QUERY: PESANAN DIBATALKAN (LEWAT BATAS PEMBAYARAN)",
        "=" * 70,
        f"waktu round-trip _find : {elapsed_ms:.3f} ms",
        f"waktu total query      : {waktu_ms:.3f} ms",
        f"pesanan diperiksa (_find, tanggal < batas) : {jumlah_kandidat}",
        f"pesanan dibatalkan     : {len(dibatalkan)}",
        "",
    ]

    if dibatalkan:
        for nomor, id_pesanan in enumerate(dibatalkan, start=1):
            lines.append(f"{nomor}. SET status:pesanan:{id_pesanan} -> dibatalkan")
    else:
        lines.append("Tidak ada pesanan yang perlu dibatalkan.")

    output = "\n".join(lines)
    print(output)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output + "\n", encoding="utf-8")
    print(f"\n>>> Hasil lengkap tersimpan di: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
