import os
import time
import requests
from dotenv import load_dotenv
from valkey import Valkey

load_dotenv()

def koneksi_couchdb():
  session = requests.Session()
  session.auth = (os.getenv("COUCH_USER"), os.getenv("COUCH_PASSWORD"))
  return session


def koneksi_valkey():
  return Valkey(
    host=os.getenv("VALKEY_HOST", "127.0.0.1"),
    port=int(os.getenv("VALKEY_PORT", "6379")),
    db=int(os.getenv("VALKEY_DB", "0")),
    decode_responses=True,
  )


def _base_url():
  return os.getenv("COUCH_URL", "http://127.0.0.1:5984").rstrip("/")


def _db_name():
  return os.getenv("COUCH_DB", "gayang")


def couch_find(couch, selector, fields=None, limit=1000):
  body = {"selector": selector, "limit": limit}
  if fields:
    body["fields"] = fields
  start = time.perf_counter()
  response = couch.post(f"{_base_url()}/{_db_name()}/_find", json=body)
  elapsed_ms = (time.perf_counter() - start) * 1000
  response.raise_for_status()
  return response.json().get("docs", []), elapsed_ms


def couch_get(couch, doc_id):
  response = couch.get(f"{_base_url()}/{_db_name()}/{doc_id}")
  if response.status_code == 404:
    return None
  response.raise_for_status()
  return response.json()


def couch_put(couch, doc):
  response = couch.put(f"{_base_url()}/{_db_name()}/{doc['_id']}", json=doc)
  response.raise_for_status()
  return response.json()


def couch_post(couch, doc):
  response = couch.post(f"{_base_url()}/{_db_name()}", json=doc)
  response.raise_for_status()
  return response.json()

def couch_bulk_docs(couch, docs):
    response = couch.post(
        f"{_base_url()}/{_db_name()}/_bulk_docs",
        json={
            "docs": docs
        }
    )
    response.raise_for_status()
    return response.json()

def couch_bulk_get(couch, ids):
    response = couch.post(
        f"{_base_url()}/{_db_name()}/_all_docs?include_docs=true",
        json={
            "keys": ids
        }
    )
    response.raise_for_status()
    rows = response.json()["rows"]
    
    return [
        r["doc"]
        for r in rows
        if "doc" in r
    ]