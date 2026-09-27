"""Shared CouchDB reads for reports, using the connection settings in .env."""

import json
import time
from decimal import Decimal, ROUND_HALF_UP

from utils.db import _base_url, _db_name, koneksi_couchdb
from utils.output import cetak_dan_simpan


def clean_id(value):
    return str(value).rsplit(":", 1)[-1]


def output_id(value):
    value = clean_id(value)
    return int(value) if value.isdigit() else value


def money(value):
    return Decimal(str(value or 0))


def rating(value):
    count = value.get("count", 0)
    if not count:
        return Decimal(0)
    return (money(value["sum"]) / count).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


class ReadClient:
    def __init__(self):
        self.session = koneksi_couchdb()
        self.url = f"{_base_url()}/{_db_name()}"

    def view(self, name, **params):
        response = self.session.get(
            f"{self.url}/_design/views/_view/{name}",
            params={key: json.dumps(value) for key, value in params.items()},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["rows"]

    def documents(self, kind, ids):
        """Fetch only referenced documents in bounded batches; omit missing joins."""
        keys = sorted({f"{kind}:{clean_id(value)}" for value in ids if value is not None})
        documents = {}
        for start in range(0, len(keys), 500):
            response = self.session.post(
                f"{self.url}/_all_docs",
                params={"include_docs": "true"},
                json={"keys": keys[start:start + 500]},
                timeout=120,
            )
            response.raise_for_status()
            for row in response.json()["rows"]:
                doc = row.get("doc")
                if doc and not doc.get("_deleted"):
                    documents[clean_id(doc["_id"])] = doc
        return documents


def paid_orders(client):
    rows = client.view("pembayaran_berhasil_per_pesanan", group=True)
    orders = client.documents("pesanan", (row["key"] for row in rows))
    for row in rows:
        order = orders.get(clean_id(row["key"]))
        if order:
            # Preserve the SQL join's multiplicity if an order has multiple payments.
            yield order, row["value"]


def rental_details(client, rows):
    orders = client.documents("pesanan", (row["key"][0] for row in rows))
    details = {
        (order_id, clean_id(detail["no_urut"])): detail
        for order_id, order in orders.items()
        for detail in order.get("detail_pesanan") or []
    }
    for row in rows:
        order_id, sequence = map(clean_id, row["key"])
        detail = details.get((order_id, sequence))
        if detail is not None:
            yield row, orders[order_id], detail


def run_report(number, title, query):
    start = time.perf_counter()
    data = query()
    cetak_dan_simpan(
        judul=f"=== {title} ===",
        data=data,
        output_file=f"results/read/query_{number}.txt",
        exec_time_ms=(time.perf_counter() - start) * 1000,
        meta_extra=["Database : CouchDB"],
    )
