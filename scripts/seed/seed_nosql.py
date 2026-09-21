import argparse
import os
from datetime import date, datetime
from decimal import Decimal

import psycopg
import requests
from dotenv import load_dotenv
from psycopg.rows import dict_row
from valkey import Valkey


# ============================================================
# CONFIGURATION / CONNECTIONS
# ============================================================

load_dotenv()

PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "gayang")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD")

COUCH_URL = os.getenv("COUCH_URL", "http://127.0.0.1:5984").rstrip("/")
COUCH_DB = os.getenv("COUCH_DB", "gayang")
COUCH_USER = os.getenv("COUCH_USER")
COUCH_PASSWORD = os.getenv("COUCH_PASSWORD")

VALKEY_HOST = os.getenv("VALKEY_HOST", "127.0.0.1")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
VALKEY_DB = int(os.getenv("VALKEY_DB", "0"))


pg = psycopg.connect(
    host=PG_HOST,
    port=PG_PORT,
    dbname=PG_DB,
    user=PG_USER,
    password=PG_PASSWORD,
    row_factory=dict_row,
)

couch = requests.Session()
couch.auth = (COUCH_USER, COUCH_PASSWORD)

vk = Valkey(
    host=VALKEY_HOST,
    port=VALKEY_PORT,
    db=VALKEY_DB,
    decode_responses=True,
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def json_safe(value):
    """Convert PostgreSQL/Python values into JSON-serializable values."""
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}

    if isinstance(value, list):
        return [json_safe(v) for v in value]

    return value


def fetch_all(sql, params=None):
    with pg.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def add_limit(sql, limit):
    if limit is None:
        return sql

    return f"{sql.rstrip().rstrip(';')} LIMIT {int(limit)}"


def couch_database_exists():
    response = couch.get(f"{COUCH_URL}/{COUCH_DB}")

    if response.status_code == 200:
        return True

    if response.status_code == 404:
        return False

    response.raise_for_status()


def create_couch_database():
    response = couch.put(f"{COUCH_URL}/{COUCH_DB}")

    # 201 = created; 412 = already exists
    if response.status_code not in (201, 202, 412):
        response.raise_for_status()


def reset_targets():
    """
    DESTRUCTIVE for target NoSQL only:
    - deletes CouchDB database COUCH_DB and recreates it
    - flushes the selected Valkey logical DB
    PostgreSQL is NOT modified.
    """
    print("\n[RESET] Membersihkan target NoSQL...")

    response = couch.delete(f"{COUCH_URL}/{COUCH_DB}")

    if response.status_code not in (200, 202, 404):
        response.raise_for_status()

    create_couch_database()
    vk.flushdb()

    print(f"[RESET] CouchDB '{COUCH_DB}' dibuat ulang.")
    print(f"[RESET] Valkey DB {VALKEY_DB} sudah FLUSHDB.")


def couch_bulk_insert(docs, batch_size=500):
    if not docs:
        return 0

    inserted = 0

    for start in range(0, len(docs), batch_size):
        batch = docs[start:start + batch_size]

        response = couch.post(
            f"{COUCH_URL}/{COUCH_DB}/_bulk_docs",
            json={"docs": json_safe(batch)},
        )
        response.raise_for_status()

        results = response.json()
        errors = [r for r in results if "error" in r]

        if errors:
            # Most common cause here is rerunning without --reset.
            raise RuntimeError(
                "CouchDB bulk insert error. "
                f"Contoh error: {errors[:3]}. "
                "Jika _id sudah ada dari test sebelumnya, jalankan ulang dengan --reset."
            )

        inserted += len(batch)
        print(f"  CouchDB: {inserted}/{len(docs)}")

    return inserted


# ============================================================
# REMOVE STATUS FIELDS FOR COUCHDB
# Status is intentionally stored in Valkey in the Project-1 model.
# ============================================================

def couch_product(row):
    row = dict(row)
    row.pop("status_produk", None)
    return row


def couch_order(row):
    row = dict(row)

    # top-level status -> Valkey
    row.pop("status_pesanan", None)

    # payment status -> Valkey
    pembayaran = row.get("pembayaran")
    if isinstance(pembayaran, dict):
        pembayaran.pop("status_pembayaran", None)

    # shipment status -> Valkey
    for pengiriman in row.get("pengiriman") or []:
        if isinstance(pengiriman, dict):
            pengiriman.pop("status_pengiriman", None)

    # rental/return status -> Valkey
    for detail in row.get("detail_pesanan") or []:
        if not isinstance(detail, dict):
            continue

        penyewaan = detail.get("penyewaan")
        if not isinstance(penyewaan, dict):
            continue

        penyewaan.pop("status_sewa", None)

        pengembalian = penyewaan.get("pengembalian")
        if isinstance(pengembalian, dict):
            pengembalian.pop("status_pengembalian", None)

    return row


def couch_room(row):
    row = dict(row)

    # message status -> Valkey
    for pesan in row.get("pesan_chat") or []:
        if isinstance(pesan, dict):
            pesan.pop("status", None)

    return row


# ============================================================
# COUCHDB SEEDING
# ============================================================

def seed_couch_pengguna(limit=None):
    print("\n=== CouchDB: pengguna ===")

    sql = add_limit(
        """
        SELECT
            id_pengguna,
            nama,
            email,
            no_telp,
            password_hash,
            tanggal_daftar,
            alamat
        FROM p1_denorm.pengguna
        ORDER BY id_pengguna
        """,
        limit,
    )

    rows = fetch_all(sql)

    docs = [
        {
            "_id": f"pengguna:{row['id_pengguna']}",
            "type": "pengguna",
            **dict(row),
        }
        for row in rows
    ]

    return couch_bulk_insert(docs)


def seed_couch_produk(limit=None):
    print("\n=== CouchDB: produk ===")

    sql = add_limit(
        """
        SELECT
            id_produk,
            id_penjual,
            nama_produk,
            deskripsi,
            ukuran,
            kondisi,
            harga_jual,
            harga_sewa,
            status_produk,
            tanggal_dibuat,
            kategori
        FROM p1_denorm.produk
        ORDER BY id_produk
        """,
        limit,
    )

    rows = fetch_all(sql)

    docs = []

    for row in rows:
        clean = couch_product(row)

        docs.append(
            {
                "_id": f"produk:{row['id_produk']}",
                "type": "produk",
                **clean,
            }
        )

    return couch_bulk_insert(docs)


def seed_couch_ulasan(limit=None):
    print("\n=== CouchDB: ulasan ===")

    sql = add_limit(
        """
        SELECT
            id_ulasan,
            id_produk,
            id_pengguna,
            rating,
            komentar,
            tanggal_ulasan
        FROM p1_denorm.ulasan
        ORDER BY id_ulasan
        """,
        limit,
    )

    rows = fetch_all(sql)

    docs = [
        {
            "_id": f"ulasan:{row['id_ulasan']}",
            "type": "ulasan",
            **dict(row),
        }
        for row in rows
    ]

    return couch_bulk_insert(docs)


def seed_couch_pesanan(limit=None):
    print("\n=== CouchDB: pesanan ===")

    sql = add_limit(
        """
        SELECT
            id_pesanan,
            id_penjual,
            id_pembeli,
            id_alamat,
            tanggal_pesanan,
            status_pesanan,
            total_pesanan,
            pembayaran,
            pengiriman,
            detail_pesanan
        FROM p1_denorm.pesanan
        ORDER BY id_pesanan
        """,
        limit,
    )

    rows = fetch_all(sql)

    docs = []

    for row in rows:
        clean = couch_order(row)

        docs.append(
            {
                "_id": f"pesanan:{row['id_pesanan']}",
                "type": "pesanan",
                **clean,
            }
        )

    return couch_bulk_insert(docs)


def seed_couch_ruang_chat(limit=None):
    print("\n=== CouchDB: ruang_chat ===")

    sql = add_limit(
        """
        SELECT
            id_ruang_chat,
            id_penjual,
            id_pembeli,
            pesan_chat
        FROM p1_denorm.ruang_chat
        ORDER BY id_ruang_chat
        """,
        limit,
    )

    rows = fetch_all(sql)

    docs = []

    for row in rows:
        clean = couch_room(row)

        docs.append(
            {
                "_id": f"ruang_chat:{row['id_ruang_chat']}",
                "type": "ruang_chat",
                **clean,
            }
        )

    return couch_bulk_insert(docs)


def seed_couchdb(limit=None):
    if not couch_database_exists():
        create_couch_database()

    total = 0
    total += seed_couch_pengguna(limit)
    total += seed_couch_produk(limit)
    total += seed_couch_ulasan(limit)
    total += seed_couch_pesanan(limit)
    total += seed_couch_ruang_chat(limit)

    print(f"\nCouchDB selesai: {total} root documents.")
    return total


# ============================================================
# VALKEY SEEDING
# ============================================================

def seed_valkey_favorit(limit=None):
    print("\n=== Valkey: produk_favorit ===")

    vk.delete("produk_favorit_count")

    sql = add_limit(
        """
        SELECT id_pengguna, id_produk
        FROM p1_denorm.valkey_favorit_export
        ORDER BY id_pengguna, id_produk
        """,
        limit,
    )

    rows = fetch_all(sql)
    pipe = vk.pipeline(transaction=False)

    for i, row in enumerate(rows, start=1):
        pipe.sadd(
            f"produk_favorit:{row['id_pengguna']}",
            row["id_produk"],
        )
        pipe.zincrby("produk_favorit_count", 1, row["id_produk"])

        if i % 5000 == 0:
            pipe.execute()

    pipe.execute()

    print(f"  Membership favorit disimpan: {len(rows)}")
    return len(rows)


def seed_valkey_ruang_chat(limit=None):
    print("\n=== Valkey: ruang_chat pengguna ===")

    sql = add_limit(
        """
        SELECT id_pengguna, id_ruang_chat
        FROM p1_denorm.valkey_ruang_chat_export
        ORDER BY id_pengguna, id_ruang_chat
        """,
        limit,
    )

    rows = fetch_all(sql)
    pipe = vk.pipeline(transaction=False)

    for i, row in enumerate(rows, start=1):
        pipe.sadd(
            f"ruang_chat:{row['id_pengguna']}",
            row["id_ruang_chat"],
        )

        if i % 5000 == 0:
            pipe.execute()

    pipe.execute()

    print(f"  Membership ruang chat disimpan: {len(rows)}")
    return len(rows)


def seed_valkey_status(limit=None):
    print("\n=== Valkey: status ===")

    sql = add_limit(
        """
        SELECT key, value
        FROM p1_denorm.valkey_status_export
        ORDER BY key
        """,
        limit,
    )

    rows = fetch_all(sql)
    pipe = vk.pipeline(transaction=False)

    for i, row in enumerate(rows, start=1):
        pipe.set(row["key"], row["value"])

        if i % 5000 == 0:
            pipe.execute()

    pipe.execute()

    print(f"  Status keys disimpan: {len(rows)}")
    return len(rows)


def seed_valkey(limit=None):
    seed_valkey_favorit(limit)
    seed_valkey_ruang_chat(limit)
    seed_valkey_status(limit)

    print("\nValkey selesai.")


# ============================================================
# VERIFICATION
# ============================================================

def postgres_count(table):
    row = fetch_all(f"SELECT COUNT(*) AS n FROM {table}")[0]
    return row["n"]


def expected_couch_count(limit=None):
    tables = [
        "p1_denorm.pengguna",
        "p1_denorm.produk",
        "p1_denorm.ulasan",
        "p1_denorm.pesanan",
        "p1_denorm.ruang_chat",
    ]

    total = 0

    for table in tables:
        n = postgres_count(table)
        total += min(n, limit) if limit is not None else n

    return total


def count_valkey_keys(pattern):
    return sum(1 for _ in vk.scan_iter(match=pattern, count=1000))


def verify(limit=None):
    print("\n================ VERIFIKASI ================")

    # PostgreSQL root aggregate counts
    print("\nPostgreSQL p1_denorm:")
    for table in [
        "p1_denorm.pengguna",
        "p1_denorm.produk",
        "p1_denorm.ulasan",
        "p1_denorm.pesanan",
        "p1_denorm.ruang_chat",
    ]:
        print(f"  {table:<28} {postgres_count(table)}")

    # CouchDB
    info = couch.get(f"{COUCH_URL}/{COUCH_DB}")
    info.raise_for_status()
    info = info.json()

    actual_docs = info["doc_count"]
    expected_docs = expected_couch_count(limit)

    print("\nCouchDB:")
    print(f"  expected root docs : {expected_docs}")
    print(f"  actual doc_count   : {actual_docs}")

    if actual_docs == expected_docs:
        print("  [OK] Jumlah root document cocok.")
    else:
        print("  [WARN] Jumlah root document belum cocok.")

    # Valkey
    print("\nValkey:")
    print(f"  DB size                    : {vk.dbsize()}")
    print(f"  produk_favorit:* keys      : {count_valkey_keys('produk_favorit:*')}")
    print(f"  ruang_chat:* keys          : {count_valkey_keys('ruang_chat:*')}")
    print(f"  status:* keys              : {count_valkey_keys('status:*')}")

    # Samples
    print("\nContoh:")
    for doc_id in ["pengguna:1", "produk:1", "pesanan:1", "ruang_chat:1"]:
        r = couch.get(f"{COUCH_URL}/{COUCH_DB}/{doc_id}")
        print(f"  CouchDB {doc_id:<16}: {'ADA' if r.status_code == 200 else 'tidak ada'}")

    sample_status = next(vk.scan_iter(match="status:*", count=100), None)
    if sample_status:
        print(f"  Valkey {sample_status} -> {vk.get(sample_status)}")

    sample_fav = next(vk.scan_iter(match="produk_favorit:*", count=100), None)
    if sample_fav:
        print(f"  Valkey {sample_fav} -> {sorted(vk.smembers(sample_fav))[:10]}")

    print("============================================")


# ============================================================
# CONNECTION TEST
# ============================================================

def test_connections():
    print("=== Test koneksi ===")

    row = fetch_all("SELECT COUNT(*) AS jumlah FROM p1_denorm.pengguna")[0]
    print("PostgreSQL pengguna:", row["jumlah"])

    r = couch.get(f"{COUCH_URL}/_session")
    r.raise_for_status()
    session = r.json()
    print("CouchDB user:", session.get("userCtx", {}).get("name"))

    print("Valkey:", vk.ping())

    # Check denormalized schema exists
    row = fetch_all(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'p1_denorm'
              AND table_name = 'pengguna'
        ) AS ada
        """
    )[0]

    if not row["ada"]:
        raise RuntimeError(
            "Schema p1_denorm belum ditemukan. "
            "Restore Project-0 lalu jalankan sql/project-1-denormalized.sql terlebih dahulu."
        )

    print("p1_denorm: OK")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Seed PostgreSQL p1_denorm -> CouchDB + Valkey"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Batasi data untuk test. Contoh: --limit 5",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Hapus target CouchDB database dan FLUSHDB Valkey sebelum seeding.",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Hanya melakukan verifikasi tanpa seeding.",
    )

    args = parser.parse_args()

    try:
        test_connections()

        if args.verify_only:
            verify(args.limit)
            return

        if args.reset:
            reset_targets()
        else:
            if not couch_database_exists():
                create_couch_database()

        print("\n============================================")
        if args.limit is None:
            print("MODE: FULL SEED")
        else:
            print(f"MODE: TEST SEED (limit={args.limit} per sumber)")
        print("============================================")

        seed_couchdb(args.limit)
        seed_valkey(args.limit)
        verify(args.limit)

    finally:
        pg.close()


if __name__ == "__main__":
    main()
