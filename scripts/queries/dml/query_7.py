from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import time
import requests

QUERIES_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = QUERIES_ROOT.parent
PROJECT_ROOT = SCRIPTS_ROOT.parent
for import_root in (QUERIES_ROOT, PROJECT_ROOT):
  if str(import_root) not in sys.path:
    sys.path.append(str(import_root))

from utils.output import cetak_dan_simpan
from scripts.valkey.valkey_access import vk, get_next_id, get_ruang_chat_pasangan, daftarkan_ruang_chat

COUCHDB_URL = "http://localhost:5984/gayang"
AUTH = ("admin_gayang", "gayang123")

session = requests.Session()
session.auth = AUTH

ID_PENJUAL = 25
ID_PEMBELI = 10
ID_PENGIRIM = 10
TEKS_PESAN = "Halo kak, apakah produk ini masih tersedia?"


def kirim_pesan():
  id_ruang_chat_set = get_ruang_chat_pasangan(ID_PENJUAL, ID_PEMBELI)
  sekarang = datetime.now(timezone.utc).astimezone().isoformat()

  if id_ruang_chat_set:
    id_ruang_chat = int(next(iter(id_ruang_chat_set)))
    room_baru = False
  else:
    id_ruang_chat = get_next_id("ruang_chat")
    room = {
      "_id": f"ruang_chat:{id_ruang_chat}",
      "type": "ruang_chat",
      "id_ruang_chat": id_ruang_chat,
      "id_penjual": ID_PENJUAL,
      "id_pembeli": ID_PEMBELI,
      "pesan_terakhir": None,
    }
    session.put(f"{COUCHDB_URL}/ruang_chat:{id_ruang_chat}", json=room)
    daftarkan_ruang_chat(ID_PENJUAL, ID_PEMBELI, id_ruang_chat)
    room_baru = True

  id_pesan = get_next_id("pesan_chat")
  pesan_baru = {
    "_id": f"pesan_chat:{id_pesan}",
    "type": "pesan_chat",
    "id_pesan": id_pesan,
    "id_ruang_chat": id_ruang_chat,
    "id_pengguna": ID_PENGIRIM,
    "pesan": TEKS_PESAN,
    "waktu_kirim": sekarang,
    "status": "terkirim",
  }
  session.put(f"{COUCHDB_URL}/pesan_chat:{id_pesan}", json=pesan_baru)

  room_doc = session.get(f"{COUCHDB_URL}/ruang_chat:{id_ruang_chat}").json()
  room_doc["pesan_terakhir"] = {
    "id_pesan": id_pesan,
    "id_pengguna": ID_PENGIRIM,
    "pesan": TEKS_PESAN,
    "waktu_kirim": sekarang,
  }
  session.put(f"{COUCHDB_URL}/ruang_chat:{id_ruang_chat}", json=room_doc)

  return [{
    "id_ruang_chat": id_ruang_chat,
    "room_baru": room_baru,
    "sumber_lookup": "Valkey (SMEMBERS ruang_chat:{}:{}".format(
        min(ID_PENJUAL, ID_PEMBELI), max(ID_PENJUAL, ID_PEMBELI)
    ) + ")",
    "id_pesan": id_pesan,
    "pesan": TEKS_PESAN,
  }]


if __name__ == "__main__":
  start_time = time.perf_counter()

  data_hasil = kirim_pesan()

  duration_ms = (time.perf_counter() - start_time) * 1000

  cetak_dan_simpan(
    judul="=== INSERT PESAN + ROOM CHAT BARU ===",
    data=data_hasil,
    output_file="results/dml/query_7.txt",
    exec_time_ms=duration_ms,
    meta_extra=["Database : CouchDB + Valkey"],
  )