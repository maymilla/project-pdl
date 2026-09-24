from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import time
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.output import cetak_dan_simpan

COUCHDB_URL = "http://localhost:5984/gayang"
AUTH = ("admin_gayang", "gayang123")

session = requests.Session()
session.auth = AUTH

ID_PENGIRIMAN = 1
NO_RESI = "JNE123456789"


def serahkan_ke_kurir():
    pengiriman = session.get(f"{COUCHDB_URL}/pengiriman:{ID_PENGIRIMAN}").json()

    if "error" in pengiriman:
        return [{"id_pengiriman": ID_PENGIRIMAN, "status": "tidak ditemukan"}]

    if pengiriman["status_pengiriman"] != "menunggu":
        return [{
            "id_pengiriman": ID_PENGIRIMAN,
            "status": f"tidak diupdate (status saat ini: {pengiriman['status_pengiriman']})",
        }]

    sekarang = datetime.now(timezone.utc).astimezone().isoformat()

    pengiriman["status_pengiriman"] = "dikirim"
    pengiriman["no_resi"] = NO_RESI
    pengiriman["tanggal_kirim"] = sekarang
    session.put(f"{COUCHDB_URL}/pengiriman:{ID_PENGIRIMAN}", json=pengiriman)

    pesanan = session.get(f"{COUCHDB_URL}/pesanan:{pengiriman['id_pesanan']}").json()
    if "error" not in pesanan:
        for entri in pesanan["pengiriman"]:
            if entri["id_pengiriman"] == ID_PENGIRIMAN:
                entri["tanggal_kirim"] = sekarang
        session.put(f"{COUCHDB_URL}/pesanan:{pesanan['id_pesanan']}", json=pesanan)

    return [{
        "id_pengiriman": ID_PENGIRIMAN,
        "status_pengiriman": "dikirim",
        "no_resi": NO_RESI,
        "tanggal_kirim": sekarang,
    }]


if __name__ == "__main__":
    start_time = time.perf_counter()

    data_hasil = serahkan_ke_kurir()

    duration_ms = (time.perf_counter() - start_time) * 1000

    cetak_dan_simpan(
        judul="=== UPDATE PENGIRIMAN SAAT DISERAHKAN KE KURIR ===",
        data=data_hasil,
        output_file="results/dml/query_8.txt",
        exec_time_ms=duration_ms,
        meta_extra=["Database : CouchDB"],
    )