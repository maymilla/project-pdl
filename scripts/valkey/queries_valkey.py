import os
import time

from dotenv import load_dotenv
from valkey import Valkey

load_dotenv()

VALKEY_HOST = os.getenv("VALKEY_HOST", "127.0.0.1")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
VALKEY_DB = int(os.getenv("VALKEY_DB", "0"))

vk = Valkey(
    host=VALKEY_HOST,
    port=VALKEY_PORT,
    db=VALKEY_DB,
    decode_responses=True,
)


def timed(label, fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"[{elapsed_ms:8.3f} ms] {label}")
    return result

# 1. PRODUK FAVORIT -> produk_favorit:{id_pengguna} = SET<id_produk>

def tambah_favorit(id_pengguna, id_produk):
    return vk.sadd(f"produk_favorit:{id_pengguna}", id_produk)


def hapus_favorit(id_pengguna, id_produk):
    return vk.srem(f"produk_favorit:{id_pengguna}", id_produk)


def get_favorit(id_pengguna):
    return vk.smembers(f"produk_favorit:{id_pengguna}")


def is_favorit(id_pengguna, id_produk):
    return vk.sismember(f"produk_favorit:{id_pengguna}", id_produk)


def jumlah_favorit(id_pengguna):
    return vk.scard(f"produk_favorit:{id_pengguna}")


# 2. RUANG CHAT -> ruang_chat:{id_pengguna} = SET<id_ruang_chat>

def daftarkan_ruang_chat(id_pengguna, id_ruang_chat):
    return vk.sadd(f"ruang_chat:{id_pengguna}", id_ruang_chat)


def keluar_ruang_chat(id_pengguna, id_ruang_chat):
    return vk.srem(f"ruang_chat:{id_pengguna}", id_ruang_chat)


def get_ruang_chat_user(id_pengguna):
    return vk.smembers(f"ruang_chat:{id_pengguna}")


def is_partisipan(id_pengguna, id_ruang_chat):
    return vk.sismember(f"ruang_chat:{id_pengguna}", id_ruang_chat)


# 3. STATUS PRODUK -> status_produk:{id_produk} = STRING

def set_status_produk(id_produk, status):
    return vk.set(f"status_produk:{id_produk}", status)


def get_status_produk(id_produk):
    return vk.get(f"status_produk:{id_produk}")


def hapus_status_produk(id_produk):
    return vk.delete(f"status_produk:{id_produk}")


# DEMO / BUKTI EKSEKUSI (untuk screenshot -> lampiran laporan)

def demo_produk_favorit():
    print("\n=== 1. Struktur: produk_favorit:{id_pengguna} (SET) ===")

    timed("SADD produk_favorit:5 -> 12", tambah_favorit, 5, 12)
    timed("SADD produk_favorit:5 -> 7", tambah_favorit, 5, 7)
    timed("SADD produk_favorit:5 -> 30", tambah_favorit, 5, 30)

    hasil = timed("SMEMBERS produk_favorit:5", get_favorit, 5)
    print(f"           -> isi set: {sorted(hasil)}")

    cek = timed("SISMEMBER produk_favorit:5, 7", is_favorit, 5, 7)
    print(f"           -> produk 7 favorit user 5? {cek}")

    jumlah = timed("SCARD produk_favorit:5", jumlah_favorit, 5)
    print(f"           -> jumlah favorit: {jumlah}")

    timed("SREM produk_favorit:5 -> 7 (unlike)", hapus_favorit, 5, 7)
    hasil = timed("SMEMBERS produk_favorit:5 (setelah unlike)", get_favorit, 5)
    print(f"           -> isi set: {sorted(hasil)}")


def demo_ruang_chat():
    print("\n=== 2. Struktur: ruang_chat:{id_pengguna} (SET) ===")

    timed("SADD ruang_chat:8 -> ruang_chat:1", daftarkan_ruang_chat, 8, "ruang_chat:1")
    timed("SADD ruang_chat:5 -> ruang_chat:1", daftarkan_ruang_chat, 5, "ruang_chat:1")
    timed("SADD ruang_chat:5 -> ruang_chat:4", daftarkan_ruang_chat, 5, "ruang_chat:4")

    hasil = timed("SMEMBERS ruang_chat:5", get_ruang_chat_user, 5)
    print(f"           -> ruang chat user 5: {sorted(hasil)}")

    cek = timed("SISMEMBER ruang_chat:8, ruang_chat:1", is_partisipan, 8, "ruang_chat:1")
    print(f"           -> user 8 partisipan ruang_chat:1? {cek}")


def demo_status_produk():
    print("\n=== 3. Struktur: status_produk:{id_produk} (STRING) ===")

    timed("SET status_produk:1 -> tersedia", set_status_produk, 1, "tersedia")
    timed("SET status_produk:7 -> disewa", set_status_produk, 7, "disewa")

    s1 = timed("GET status_produk:1", get_status_produk, 1)
    print(f"           -> status_produk:1 = {s1}")

    timed("SET status_produk:1 -> terjual (update)", set_status_produk, 1, "terjual")
    s1 = timed("GET status_produk:1 (setelah update)", get_status_produk, 1)
    print(f"           -> status_produk:1 = {s1}")


def ringkasan_db():
    print("\n=== Ringkasan Valkey DB ===")
    print(f"DB size total keys : {vk.dbsize()}")
    print(f"produk_favorit:*    : {sum(1 for _ in vk.scan_iter(match='produk_favorit:*'))} keys")
    print(f"ruang_chat:*        : {sum(1 for _ in vk.scan_iter(match='ruang_chat:*'))} keys")
    print(f"status_produk:*     : {sum(1 for _ in vk.scan_iter(match='status_produk:*'))} keys")


def main():
    print("=== Koneksi Valkey ===")
    print(f"Host: {VALKEY_HOST}:{VALKEY_PORT}  DB: {VALKEY_DB}")
    print(f"PING -> {vk.ping()}")

    demo_produk_favorit()
    demo_ruang_chat()
    demo_status_produk()
    ringkasan_db()


if __name__ == "__main__":
    main()
