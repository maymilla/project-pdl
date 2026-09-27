import json
from pathlib import Path
import sys
import time
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.queries.utils.db import _base_url, _db_name, koneksi_couchdb, couch_bulk_docs
from scripts.queries.utils.output import cetak_dan_simpan

couch = koneksi_couchdb()

def key(value):
    return str(value).rsplit(":", 1)[-1]

def load_documents(kind):
    params = {
        "include_docs": "true", "limit": 500,
        "startkey": json.dumps(kind + ":"), "endkey": json.dumps(kind + ":\ufff0"),
    }
    documents = {}
    while True:
        response = couch.get(f"{_base_url()}/{_db_name()}/_all_docs", params=params, timeout=120)
        response.raise_for_status()
        rows = response.json()["rows"]
        for row in rows:
            document = row.get("doc")
            if document and not document.get("_deleted") and document.get("type") == kind:
                documents[key(document["_id"])] = document
        if len(rows) < 500:
            return documents
        params = {**params, "startkey": json.dumps(rows[-1]["id"]), "skip": 1}

def batalkan_pesanan():
    cutoff = datetime.now().astimezone() - timedelta(hours=24)
    paid = {
        key(payment["id_pesanan"]) for payment in load_documents("pembayaran").values()
        if payment.get("status_pembayaran") == "berhasil"
    }
    candidates = []
    for order in load_documents("pesanan").values():
        if order.get("status_pesanan") != "menunggu_pembayaran":
            continue
        if key(order.get("id_pesanan", order["_id"])) in paid or not order.get("tanggal_pesanan"):
            continue
        created = datetime.fromisoformat(order["tanggal_pesanan"])
        created = created.astimezone()
        if created < cutoff:
            candidates.append(order)
    results = []
    for document in candidates:
        document["status_pesanan"] = "dibatalkan"
    for start in range(0, len(candidates), 500):
        results.extend(couch_bulk_docs(couch, candidates[start:start + 500]))
    return results

if __name__ == "__main__":
    start = time.perf_counter()
    results = batalkan_pesanan()
    cetak_dan_simpan(
        judul="QUERY 9 DML: batalkan pesanan",
        data=results,
        output_file=PROJECT_ROOT / "results/dml/query_9.txt",
        exec_time_ms=(time.perf_counter() - start) * 1000,
        meta_extra=["Database : CouchDB"],
    )
