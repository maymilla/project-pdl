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


# 2. RUANG CHAT -> ruang_chat:{user1}:{user2} = SET<id_ruang_chat>

def _pair_key(id_pengguna_a, id_pengguna_b):
    user1 = min(id_pengguna_a, id_pengguna_b)
    user2 = max(id_pengguna_a, id_pengguna_b)
    return f"ruang_chat:{user1}:{user2}"


def daftarkan_ruang_chat(id_penjual, id_pembeli, id_ruang_chat):
    return vk.sadd(_pair_key(id_penjual, id_pembeli), id_ruang_chat)


def hapus_ruang_chat(id_penjual, id_pembeli, id_ruang_chat):
    return vk.srem(_pair_key(id_penjual, id_pembeli), id_ruang_chat)


def get_ruang_chat_pasangan(id_penjual, id_pembeli):
    """Cari id_ruang_chat yang sudah ada antara dua user ini (kalau ada)."""
    return vk.smembers(_pair_key(id_penjual, id_pembeli))


def sudah_pernah_chat(id_penjual, id_pembeli):
    return vk.exists(_pair_key(id_penjual, id_pembeli)) == 1


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
    print("\n=== 2. Struktur: ruang_chat:{user1}:{user2} (SET, key di-sort) ===")

    timed("SADD ruang_chat:5:8 -> 1 (penjual=8, pembeli=5)", daftarkan_ruang_chat, 8, 5, 1)

    cek = timed("EXISTS ruang_chat:5:8 (lookup penjual=8,pembeli=5)", sudah_pernah_chat, 8, 5)
    print(f"           -> sudah pernah chat? {cek}")

    hasil = timed("SMEMBERS ruang_chat:5:8", get_ruang_chat_pasangan, 8, 5)
    print(f"           -> id_ruang_chat: {sorted(hasil)}")

    cek_terbalik = timed("EXISTS ruang_chat:5:8 (lookup dibalik penjual=5,pembeli=8)", sudah_pernah_chat, 5, 8)
    print(f"           -> tetap ketemu walau urutan dibalik? {cek_terbalik}")


def ringkasan_db():
    print("\n=== Ringkasan Valkey DB ===")
    print(f"DB size total keys : {vk.dbsize()}")
    print(f"produk_favorit:*    : {sum(1 for _ in vk.scan_iter(match='produk_favorit:*'))} keys")
    print(f"ruang_chat:*        : {sum(1 for _ in vk.scan_iter(match='ruang_chat:*'))} keys")


def main():
    print("=== Koneksi Valkey ===")
    print(f"Host: {VALKEY_HOST}:{VALKEY_PORT}  DB: {VALKEY_DB}")
    print(f"PING -> {vk.ping()}")

    demo_produk_favorit()
    demo_ruang_chat()
    ringkasan_db()


if __name__ == "__main__":
    main()