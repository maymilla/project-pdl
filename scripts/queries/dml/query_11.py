import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.queries.utils.db import _base_url, _db_name, koneksi_couchdb, couch_bulk_docs, couch_bulk_get
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

def tandai_produk_disewa():
    rentals = [
        rental for rental in load_documents("penyewaan").values()
        if rental.get("status_sewa") == "berjalan"
    ]
    orders = load_documents("pesanan")
    product_ids = set()
    for rental in rentals:
        order = orders.get(key(rental["id_pesanan"]), {})
        for detail in order.get("detail_pesanan") or []:
            if detail["no_urut"] == rental["no_urut"]:
                product_ids.add("produk:" + key(detail["id_produk"]))
    products = []
    ids = sorted(product_ids)
    for start in range(0, len(ids), 500):
        products.extend(couch_bulk_get(couch, ids[start:start + 500]))
    candidates = [
        product for product in products
        if product.get("status_produk") is not None and product["status_produk"] != "disewa"
    ]
    results = []
    for document in candidates:
        document["status_produk"] = "disewa"
    for start in range(0, len(candidates), 500):
        results.extend(couch_bulk_docs(couch, candidates[start:start + 500]))
    return results

if __name__ == "__main__":
    start = time.perf_counter()
    results = tandai_produk_disewa()
    cetak_dan_simpan(
        judul="QUERY 11 DML: tandai produk disewa",
        data=results,
        output_file=PROJECT_ROOT / "results/dml/query_11.txt",
        exec_time_ms=(time.perf_counter() - start) * 1000,
        meta_extra=["Database : CouchDB"],
    )
