import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from valkey import Valkey

load_dotenv()

COUCH_URL = os.getenv("COUCH_URL", "http://127.0.0.1:5984").rstrip("/")
COUCH_DB = os.getenv("COUCH_DB", "gayang")
COUCH_USER = os.getenv("COUCH_USER")
COUCH_PASSWORD = os.getenv("COUCH_PASSWORD")

VALKEY_HOST = os.getenv("VALKEY_HOST", "127.0.0.1")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
VALKEY_DB = int(os.getenv("VALKEY_DB", "0"))

couch = requests.Session()
couch.auth = (COUCH_USER, COUCH_PASSWORD)

vk = Valkey(
    host=VALKEY_HOST,
    port=VALKEY_PORT,
    db=VALKEY_DB,
    decode_responses=True,
)

OUTPUT_FILE = Path(__file__).resolve().parents[3] / "results" / "dml_5_8_results.txt"
_log_lines = []


def log(text=""):
    print(text)
    _log_lines.append(str(text))


def save_log():
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        f.write("\n".join(_log_lines))
    print(f"\n>>> Hasil lengkap tersimpan di: {OUTPUT_FILE}")


def pretty(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


def section(title):
    log("\n" + "=" * 70)
    log(title)
    log("=" * 70)


def couch_find(selector, fields=None, limit=1000):
    body = {"selector": selector, "execution_stats": True, "limit": limit}
    if fields:
        body["fields"] = fields

    start = time.perf_counter()
    r = couch.post(f"{COUCH_URL}/{COUCH_DB}/_find", json=body)
    elapsed_ms = (time.perf_counter() - start) * 1000
    r.raise_for_status()
    return r.json(), elapsed_ms


def couch_get(doc_id):
    start = time.perf_counter()
    r = couch.get(f"{COUCH_URL}/{COUCH_DB}/{doc_id}")
    elapsed_ms = (time.perf_counter() - start) * 1000
    r.raise_for_status()
    return r.json(), elapsed_ms


def couch_put(doc):
    start = time.perf_counter()
    r = couch.put(f"{COUCH_URL}/{COUCH_DB}/{doc['_id']}", json=doc)
    elapsed_ms = (time.perf_counter() - start) * 1000
    r.raise_for_status()
    return r.json(), elapsed_ms


def create_index(fields, name):
    r = couch.post(f"{COUCH_URL}/{COUCH_DB}/_index", json={
        "index": {"fields": fields},
        "name": name,
        "type": "json",
    })
    r.raise_for_status()
    return r.json()


def cari_pengiriman_gagal_kirim(batas_hari=3, sample_limit=500):
    batas_waktu = (datetime.utcnow() - timedelta(days=batas_hari)).isoformat()

    selector = {
        "type": "pesanan",
        "tanggal_pesanan": {"$gte": batas_waktu},
    }
    result, elapsed = couch_find(
        selector,
        fields=["_id", "_rev", "pengiriman", "tanggal_pesanan"],
        limit=sample_limit,
    )

    stats = result.get("execution_stats", {})
    docs = result.get("docs", [])

    target = []
    for doc in docs:
        pengiriman_list = doc.get("pengiriman") or []
        if not pengiriman_list or len(pengiriman_list) > 1:
            continue  # sudah lebih dari 1 elemen -> sudah pernah di-retry

        id_pengiriman = pengiriman_list[0].get("id_pengiriman")
        status = vk.get(f"status:pengiriman:{id_pengiriman}")

        if status == "gagal_kirim":
            target.append(doc)

    return target, elapsed, stats


def cari_pesanan_batal_kandidat(batas_jam=24, sample_limit=500):
    batas_waktu = (datetime.utcnow() - timedelta(hours=batas_jam)).isoformat()

    selector = {
        "type": "pesanan",
        "tanggal_pesanan": {"$lt": batas_waktu},
    }
    result, elapsed = couch_find(
        selector,
        fields=["_id", "_rev", "pembayaran", "pengiriman", "tanggal_pesanan"],
        limit=sample_limit,
    )

    stats = result.get("execution_stats", {})
    docs = result.get("docs", [])

    target = []
    for doc in docs:
        status_pesanan = vk.get(f"status:pesanan:{doc['_id'].split(':')[1]}")
        if status_pesanan in ("selesai", "dibatalkan"):
            continue

        pengiriman_list = doc.get("pengiriman") or []
        if not pengiriman_list:
            continue

        id_pengiriman = pengiriman_list[0].get("id_pengiriman")
        status_kirim = vk.get(f"status:pengiriman:{id_pengiriman}")

        if status_kirim == "gagal_kirim":
            target.append(doc)

    return target, elapsed, stats


def cari_room_chat(id_penjual, id_pembeli):
    selector = {
        "type": "ruang_chat",
        "id_penjual": id_penjual,
        "id_pembeli": id_pembeli,
    }
    result, elapsed = couch_find(selector, fields=["_id", "_rev", "pesan_chat"])
    return result, elapsed

# QUERY 5  -- INSERT riwayat pengiriman ulang

def run_query5(fase, eksekusi_tulis):
    section(f"[{fase}] QUERY 5: INSERT riwayat pengiriman ulang")

    target, elapsed, stats = cari_pengiriman_gagal_kirim()
    log(f"waktu round-trip _find      : {elapsed:.3f} ms")
    log(f"docs_examined               : {stats.get('total_docs_examined')}")
    log(f"kandidat diperiksa (_find)  : {stats.get('results_returned')}")
    log(f"target gagal_kirim (Valkey) : {len(target)}")

    if not eksekusi_tulis:
        return

    log(f"\n--- Eksekusi INSERT riwayat pengiriman (maks 3 demo) ---")
    updated = 0
    for doc in target[:3]:
        pengiriman_lama = doc["pengiriman"][0]
        id_pengiriman_baru = int(time.time() * 1000) + updated

        percobaan_baru = {
            "kurir": pengiriman_lama.get("kurir"),
            "no_resi": None,
            "id_pengiriman": id_pengiriman_baru,
            "tanggal_kirim": None,
            "tanggal_terima": None,
        }
        doc["pengiriman"].append(percobaan_baru)

        _, put_elapsed = couch_put(doc)
        log(f"  PUT {doc['_id']} (INSERT percobaan ke-{len(doc['pengiriman'])}) -> {put_elapsed:.3f} ms")

        vk.set(f"status:pengiriman:{id_pengiriman_baru}", "menunggu")
        log(f"  SET status:pengiriman:{id_pengiriman_baru} -> menunggu")
        updated += 1

    log(f"\nTotal kandidat ditemukan : {len(target)}")
    log(f"Total di-INSERT (demo)   : {updated}")


# QUERY 6 -- UPDATE pesanan dibatalkan + pembayaran refund

def run_query6(fase, eksekusi_tulis):
    section(f"[{fase}] QUERY 6: UPDATE pesanan dibatalkan + pembayaran refund")

    target, elapsed, stats = cari_pesanan_batal_kandidat()
    log(f"waktu round-trip _find     : {elapsed:.3f} ms")
    log(f"docs_examined              : {stats.get('total_docs_examined')}")
    log(f"target batal (Valkey)      : {len(target)}")

    if not eksekusi_tulis:
        return

    log(f"\n--- Eksekusi UPDATE batal + refund (maks 3 demo) ---")
    updated = 0
    for doc in target[:3]:
        id_pesanan_num = doc["_id"].split(":")[1]
        id_pembayaran = doc.get("pembayaran", {}).get("id_pembayaran")

        vk.set(f"status:pesanan:{id_pesanan_num}", "dibatalkan")
        log(f"  SET status:pesanan:{id_pesanan_num} -> dibatalkan")

        status_bayar = vk.get(f"status:pembayaran:{id_pembayaran}")
        if status_bayar == "berhasil":
            vk.set(f"status:pembayaran:{id_pembayaran}", "refund")
            log(f"  SET status:pembayaran:{id_pembayaran} -> refund")

        updated += 1

    log(f"\nTotal kandidat ditemukan : {len(target)}")
    log(f"Total di-UPDATE (demo)   : {updated}")


# QUERY 7 -- INSERT pesan + room chat baru

def run_query7(fase, eksekusi_tulis, id_penjual=25, id_pembeli=10):
    section(f"[{fase}] QUERY 7: INSERT pesan + room chat baru")

    result, elapsed = cari_room_chat(id_penjual, id_pembeli)
    stats = result.get("execution_stats", {})
    docs = result.get("docs", [])

    log(f"waktu round-trip _find : {elapsed:.3f} ms")
    log(f"docs_examined          : {stats.get('total_docs_examined')}")
    log(f"results_returned       : {stats.get('results_returned')}")
    if "warning" in result:
        log(f"warning: {result['warning']}")

    if not eksekusi_tulis:
        return

    pesan_baru = "Halo kak, apakah produk ini masih tersedia?"

    if docs:
        room, _ = couch_get(docs[0]["_id"])
        log(f"\nRoom sudah ada: {room['_id']} -> INSERT pesan baru ke array pesan_chat")
    else:
        room_id = f"ruang_chat:test_{id_penjual}_{id_pembeli}_{int(time.time())}"
        room = {
            "_id": room_id,
            "type": "ruang_chat",
            "id_penjual": id_penjual,
            "id_pembeli": id_pembeli,
            "pesan_chat": [],
        }
        _, put_elapsed = couch_put(room)
        log(f"\nRoom belum ada -> INSERT dokumen ruang_chat baru {room_id} -> {put_elapsed:.3f} ms")

        vk.sadd(f"ruang_chat:{id_penjual}", room_id)
        vk.sadd(f"ruang_chat:{id_pembeli}", room_id)
        log(f"SADD ruang_chat:{id_penjual} -> {room_id}")
        log(f"SADD ruang_chat:{id_pembeli} -> {room_id}")

        room, _ = couch_get(room_id)

    room.setdefault("pesan_chat", []).append({
        "id_pesan": len(room["pesan_chat"]) + 1,
        "id_pengirim": id_pembeli,
        "pesan": pesan_baru,
        "waktu_kirim": datetime.utcnow().isoformat(),
    })

    _, put_elapsed = couch_put(room)
    log(f"PUT (INSERT pesan) ke {room['_id']} -> {put_elapsed:.3f} ms")

    id_pesan_baru = room["pesan_chat"][-1]["id_pesan"]
    vk.set(f"status:pesan_chat:{room['_id']}:{id_pesan_baru}", "terkirim")
    log(f"SET status:pesan_chat:{room['_id']}:{id_pesan_baru} -> terkirim")


# QUERY 8 -- UPDATE status pengiriman (operasi yang memang tak perlu index, karena akses langsung by _id)

def run_query8(fase, id_pesanan="pesanan:1"):
    section(f"[{fase}] QUERY 8: UPDATE status pengiriman (TANPA index -- akses langsung by _id)")

    try:
        doc, get_elapsed = couch_get(id_pesanan)
    except requests.HTTPError:
        log(f"Dokumen {id_pesanan} tidak ditemukan, lewati.")
        return

    log(f"GET {id_pesanan} -> {get_elapsed:.3f} ms")

    pengiriman_list = doc.get("pengiriman")
    if not pengiriman_list or not isinstance(pengiriman_list, list):
        log(f"Dokumen {id_pesanan} tidak punya array 'pengiriman', lewati.")
        return

    pengiriman = pengiriman_list[0]
    id_pengiriman = pengiriman.get("id_pengiriman")

    pengiriman["no_resi"] = "JNE123456789"
    pengiriman["tanggal_kirim"] = datetime.utcnow().isoformat()

    _, put_elapsed = couch_put(doc)
    log(f"PUT {id_pesanan} (UPDATE no_resi & tanggal_kirim) -> {put_elapsed:.3f} ms")

    vk.set(f"status:pengiriman:{id_pengiriman}", "dikirim")
    log(f"SET status:pengiriman:{id_pengiriman} -> dikirim")


def main():
    log(f"=== Test Query DML 5-8 (CouchDB + Valkey hybrid) ===")
    log(f"Waktu jalan  : {datetime.now().isoformat()}")
    log(f"CouchDB URL  : {COUCH_URL}  DB: {COUCH_DB}")
    log(f"Valkey       : {VALKEY_HOST}:{VALKEY_PORT} DB {VALKEY_DB}")

    # sebelum index
    section("FASE 1: MENJALANKAN SEMUA QUERY SEBELUM ADA INDEX")
    run_query5("SEBELUM INDEX", eksekusi_tulis=True)
    run_query6("SEBELUM INDEX", eksekusi_tulis=True)
    run_query7("SEBELUM INDEX", eksekusi_tulis=True)
    run_query8("SEBELUM INDEX")

    # buat index
    section("FASE 2: MEMBUAT SEMUA INDEX")

    idx1 = create_index(["type", "tanggal_pesanan"], "idx-pesanan-tanggal")
    log(f"Index dibuat: {pretty(idx1)}")

    idx2 = create_index(
        ["type", "id_penjual", "id_pembeli"],
        "idx-ruangchat-penjual-pembeli",
    )
    log(f"Index dibuat: {pretty(idx2)}")

    log("\nCatatan: query 5 & 6 sama-sama memakai index idx-pesanan-tanggal")
    log("(field type + tanggal_pesanan), sehingga cukup 1 index untuk dua-duanya.")
    log("Query 8 sengaja TIDAK diberi index apa pun (akses langsung by _id).")

    # warm-up call (agar index dibangun)
    section("FASE 3: WARM-UP CALL (hasil dibuang, memaksa index selesai dibangun)")

    t0 = time.perf_counter()
    run_query5("WARM-UP", eksekusi_tulis=False)
    run_query6("WARM-UP", eksekusi_tulis=False)
    run_query7("WARM-UP", eksekusi_tulis=False)
    t1 = time.perf_counter()
    log(f"\nTotal waktu warm-up: {(t1 - t0) * 1000:.3f} ms (angka ini TIDAK dipakai sebagai hasil akhir)")

    # jeda kecil supaya index benar-benar settle sebelum diukur
    time.sleep(1)

    # setelah index + warm-up
    section("FASE 4: MENJALANKAN SEMUA QUERY SETELAH INDEX + WARM-UP")
    run_query5("SETELAH INDEX", eksekusi_tulis=True)
    run_query6("SETELAH INDEX", eksekusi_tulis=True)
    run_query7("SETELAH INDEX", eksekusi_tulis=True)
    run_query8("SETELAH INDEX")

    save_log()


if __name__ == "__main__":
    main()
