import json
from pathlib import Path
import sys
import time

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

def selesaikan_penyewaan():
    returns = load_documents("pengembalian")
    rentals = []
    for rental in load_documents("penyewaan").values():
        return_id = (rental.get("pengembalian") or {}).get("id_pengembalian")
        returned = returns.get(key(return_id), {})
        if returned.get("status_pengembalian") == "selesai":
            rentals.append(rental)
    candidates = rentals
    results = []
    for document in candidates:
        document["status_sewa"] = "selesai"
    for start in range(0, len(candidates), 500):
        results.extend(couch_bulk_docs(couch, candidates[start:start + 500]))
    return results

if __name__ == "__main__":
    start = time.perf_counter()
    results = selesaikan_penyewaan()
    cetak_dan_simpan(
        judul="QUERY 10 DML: selesaikan penyewaan",
        data=results,
        output_file=PROJECT_ROOT / "results/dml/query_10.txt",
        exec_time_ms=(time.perf_counter() - start) * 1000,
        meta_extra=["Database : CouchDB"],
    )
