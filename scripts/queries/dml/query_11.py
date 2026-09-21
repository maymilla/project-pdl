import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from valkey import Valkey


ROOT_DIR = Path(__file__).resolve().parents[3]
OUTPUT_FILE = ROOT_DIR / "results" / "dml" / "query_11.txt"


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


def cari_produk_dari_penyewaan(couch, id_penyewaan):
    docs, elapsed_ms = couch_find(
        couch,
        {
            "type": "pesanan",
            "detail_pesanan": {"$elemMatch": {"penyewaan.id_penyewaan": id_penyewaan}},
        },
        fields=["_id", "detail_pesanan"],
        limit=10,
    )

    for doc in docs:
        for detail in doc.get("detail_pesanan") or []:
            penyewaan = detail.get("penyewaan")
            if isinstance(penyewaan, dict) and penyewaan.get("id_penyewaan") == id_penyewaan:
                return detail.get("id_produk"), elapsed_ms

    return None, elapsed_ms


def mulai_penyewaan_produk(couch, valkey, id_penyewaan, eksekusi_tulis=True):
    id_produk, elapsed_ms = cari_produk_dari_penyewaan(couch, id_penyewaan)

    if id_produk is None:
        return None, None, elapsed_ms

    status_sewa = valkey.get(f"status:penyewaan:{id_penyewaan}")
    diperbarui = False

    if status_sewa == "berjalan":
        if eksekusi_tulis:
            valkey.set(f"status:produk:{id_produk}", "disewa")
        diperbarui = True

    return id_produk, diperbarui, elapsed_ms


def main():
    parser = argparse.ArgumentParser(
        description="Query 11 (DML NoSQL): tandai produk sedang disewa saat penyewaan dimulai."
    )
    parser.add_argument("--id-penyewaan", type=int, default=1, help="id_penyewaan acuan (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Hanya tampilkan hasil tanpa menulis ke Valkey")
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    couch = koneksi_couchdb()
    valkey = koneksi_valkey()

    mulai = time.perf_counter()
    id_produk, diperbarui, elapsed_ms = mulai_penyewaan_produk(
        couch, valkey, args.id_penyewaan, eksekusi_tulis=not args.dry_run
    )
    waktu_ms = (time.perf_counter() - mulai) * 1000

    lines = [
        "=== Query 11 (DML): Produk Disewa Saat Penyewaan Dimulai (NoSQL) ===",
        f"Waktu jalan  : {datetime.now().isoformat()}",
        f"CouchDB      : {os.getenv('COUCH_URL', 'http://127.0.0.1:5984')}  DB: {os.getenv('COUCH_DB', 'gayang')}",
        f"Valkey       : {os.getenv('VALKEY_HOST', '127.0.0.1')}:{os.getenv('VALKEY_PORT', '6379')}  DB: {os.getenv('VALKEY_DB', '0')}",
        f"mode         : {'DRY-RUN (tanpa tulis)' if args.dry_run else 'EKSEKUSI (tulis ke Valkey)'}",
        "",
        "=" * 70,
        f"HASIL QUERY: PRODUK DISEWA (id_penyewaan={args.id_penyewaan})",
        "=" * 70,
        f"waktu round-trip _find : {elapsed_ms:.3f} ms",
        f"waktu total query      : {waktu_ms:.3f} ms",
        "",
    ]

    if id_produk is None:
        lines.append(f"Tidak ditemukan detail penyewaan untuk id_penyewaan={args.id_penyewaan}.")
    elif diperbarui:
        lines.append(f"SET status:produk:{id_produk} -> disewa")
    else:
        lines.append(
            f"id_produk={id_produk} ditemukan, tapi status_sewa belum 'berjalan' -> tidak diperbarui."
        )

    output = "\n".join(lines)
    print(output)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output + "\n", encoding="utf-8")
    print(f"\n>>> Hasil lengkap tersimpan di: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
