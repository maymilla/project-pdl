import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from valkey import Valkey


ROOT_DIR = Path(__file__).resolve().parents[3]
OUTPUT_FILE = ROOT_DIR / "results" / "dml" / "query_12.txt"


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


def cari_pengembalian_selesai_untuk_produk(couch, valkey, id_produk):
    docs, elapsed_ms = couch_find(
        couch,
        {
            "type": "pesanan",
            "detail_pesanan": {"$elemMatch": {"id_produk": id_produk}},
        },
        fields=["_id", "detail_pesanan"],
        limit=10000,
    )

    id_pengembalian_selesai = []
    for doc in docs:
        for detail in doc.get("detail_pesanan") or []:
            if detail.get("id_produk") != id_produk:
                continue

            penyewaan = detail.get("penyewaan")
            if not isinstance(penyewaan, dict):
                continue

            pengembalian = penyewaan.get("pengembalian")
            if not isinstance(pengembalian, dict):
                continue

            id_pengembalian = pengembalian.get("id_pengembalian")
            if id_pengembalian is None:
                continue

            if valkey.get(f"status:pengembalian:{id_pengembalian}") == "selesai":
                id_pengembalian_selesai.append(id_pengembalian)

    return id_pengembalian_selesai, elapsed_ms


def sediakan_kembali_produk(couch, valkey, id_produk, eksekusi_tulis=True):
    id_pengembalian_selesai, elapsed_ms = cari_pengembalian_selesai_untuk_produk(couch, valkey, id_produk)

    diperbarui = False
    if id_pengembalian_selesai:
        if eksekusi_tulis:
            valkey.set(f"status:produk:{id_produk}", "tersedia")
        diperbarui = True

    return id_pengembalian_selesai, diperbarui, elapsed_ms


def main():
    parser = argparse.ArgumentParser(
        description="Query 12 (DML NoSQL): kembalikan status produk menjadi tersedia setelah pengembalian selesai."
    )
    parser.add_argument("--id-produk", type=int, default=1756, help="id_produk acuan (default: 1756)")
    parser.add_argument("--dry-run", action="store_true", help="Hanya tampilkan hasil tanpa menulis ke Valkey")
    args = parser.parse_args()

    load_dotenv(ROOT_DIR / ".env")
    couch = koneksi_couchdb()
    valkey = koneksi_valkey()

    mulai = time.perf_counter()
    id_pengembalian_selesai, diperbarui, elapsed_ms = sediakan_kembali_produk(
        couch, valkey, args.id_produk, eksekusi_tulis=not args.dry_run
    )
    waktu_ms = (time.perf_counter() - mulai) * 1000

    lines = [
        "=== Query 12 (DML): Produk Tersedia Kembali Setelah Pengembalian (NoSQL) ===",
        f"Waktu jalan  : {datetime.now().isoformat()}",
        f"CouchDB      : {os.getenv('COUCH_URL', 'http://127.0.0.1:5984')}  DB: {os.getenv('COUCH_DB', 'gayang')}",
        f"Valkey       : {os.getenv('VALKEY_HOST', '127.0.0.1')}:{os.getenv('VALKEY_PORT', '6379')}  DB: {os.getenv('VALKEY_DB', '0')}",
        f"mode         : {'DRY-RUN (tanpa tulis)' if args.dry_run else 'EKSEKUSI (tulis ke Valkey)'}",
        "",
        "=" * 70,
        f"HASIL QUERY: PRODUK TERSEDIA KEMBALI (id_produk={args.id_produk})",
        "=" * 70,
        f"waktu round-trip _find : {elapsed_ms:.3f} ms",
        f"waktu total query      : {waktu_ms:.3f} ms",
        f"pengembalian selesai ditemukan : {len(id_pengembalian_selesai)}",
        "",
    ]

    if diperbarui:
        lines.append(f"SET status:produk:{args.id_produk} -> tersedia")
        lines.append(f"(dipicu oleh id_pengembalian: {id_pengembalian_selesai})")
    else:
        lines.append(
            f"Tidak ada pengembalian berstatus 'selesai' untuk id_produk={args.id_produk} -> tidak diperbarui."
        )

    output = "\n".join(lines)
    print(output)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output + "\n", encoding="utf-8")
    print(f"\n>>> Hasil lengkap tersimpan di: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
