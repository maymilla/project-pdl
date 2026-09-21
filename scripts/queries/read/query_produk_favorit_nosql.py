import argparse
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from valkey import Valkey


ROOT_DIR = Path(__file__).resolve().parents[3]
OUTPUT_FILE = ROOT_DIR / "results" / "produk_favorit_nosql_results.txt"


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


def ambil_produk_dan_penjual(couch, id_produk):
    base_url = os.getenv("COUCH_URL", "http://127.0.0.1:5984").rstrip("/")
    database = os.getenv("COUCH_DB", "gayang")

    produk_response = couch.get(f"{base_url}/{database}/produk:{id_produk}")
    if produk_response.status_code == 404:
        return None
    produk_response.raise_for_status()
    produk = produk_response.json()

    id_penjual = produk.get("id_penjual")
    penjual_response = couch.get(f"{base_url}/{database}/pengguna:{id_penjual}")
    if penjual_response.status_code == 404:
        nama_penjual = "(data penjual tidak ditemukan)"
    else:
        penjual_response.raise_for_status()
        nama_penjual = penjual_response.json().get("nama", "(tanpa nama)")

    return {
        "id_produk": id_produk,
        "nama_produk": produk.get("nama_produk", "(tanpa nama)"),
        "id_penjual": id_penjual,
        "nama_penjual": nama_penjual,
    }


def ambil_produk_favorit_nosql(limit):
    valkey = koneksi_valkey()
    couch = koneksi_couchdb()
    jumlah_favorit = Counter()

    for key in valkey.scan_iter(match="produk_favorit:*"):
        jumlah_favorit.update(valkey.smembers(key))

    hasil = []
    produk_terurut = sorted(
        jumlah_favorit.items(),
        key=lambda item: (-item[1], int(item[0])),
    )
    for id_produk, total_favorit in produk_terurut:
        detail = ambil_produk_dan_penjual(couch, id_produk)
        if detail is None:
            continue
        detail["total_favorit"] = total_favorit
        hasil.append(detail)
        if len(hasil) == limit:
            break

    return hasil, len(jumlah_favorit)


def main():
    parser = argparse.ArgumentParser(
        description="Agregasi produk favorit dari Valkey dan detail dari CouchDB."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Jumlah produk yang ditampilkan (default: 10).",
    )
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit harus lebih besar dari 0")

    load_dotenv(ROOT_DIR / ".env")
    mulai = time.perf_counter()
    rows, produk_teragregasi = ambil_produk_favorit_nosql(args.limit)
    waktu_ms = (time.perf_counter() - mulai) * 1000

    lines = [
        "=== Query Produk Paling Sering Difavoritkan (NoSQL) ===",
        f"Waktu jalan  : {datetime.now().isoformat()}",
        f"CouchDB      : {os.getenv('COUCH_URL', 'http://127.0.0.1:5984')}  DB: {os.getenv('COUCH_DB', 'gayang')}",
        f"Valkey       : {os.getenv('VALKEY_HOST', '127.0.0.1')}:{os.getenv('VALKEY_PORT', '6379')}  DB: {os.getenv('VALKEY_DB', '0')}",
        "",
        "=" * 70,
        "HASIL QUERY: PRODUK PALING SERING DIFAVORITKAN",
        "=" * 70,
        f"waktu query  : {waktu_ms:.3f} ms",
        f"produk dihitung dari Valkey : {produk_teragregasi}",
        f"jumlah hasil : {len(rows)}",
        "",
    ]

    if rows:
        for nomor, row in enumerate(rows, start=1):
            lines.append(
                f"{nomor}. {row['nama_produk']} "
                f"(id_produk={row['id_produk']}) - "
                f"{row['total_favorit']} favorit - "
                f"penjual: {row['nama_penjual']} "
                f"(id_penjual={row['id_penjual']})"
            )
    else:
        lines.append(
            "Tidak ada data favorit. Jalankan seed_nosql.py terlebih dahulu "
            "atau isi key produk_favorit:{id_pengguna} di Valkey."
        )

    output = "\n".join(lines)
    print(output)
    OUTPUT_FILE.write_text(output + "\n", encoding="utf-8")
    print(f"\n>>> Hasil lengkap tersimpan di: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()