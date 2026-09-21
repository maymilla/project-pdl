# Project PDL

Project ini berisi baseline PostgreSQL denormalisasi, seed CouchDB/Valkey, dan query pembanding.

## Struktur

```text
sql/
  project_0_db.dump
  project-1-denormalized.sql
  queries/
    produk_favorit_terpopuler.sql
scripts/
  queries/read/query_produk_favorit_nosql.py
  queries/dml/dml_5_8.py
  seed/seed_nosql.py
  seed/seed_recent_gagal_kirim.py
  valkey/queries_valkey.py
results/
  dml_5_8_results.txt
```

## Query produk favorit

1. Nyalakan CouchDB dan Valkey:

```powershell
docker compose up -d
docker compose ps
```

2. Pastikan PostgreSQL aktif dan `.env` mengarah ke database `gayang`.

3. Jalankan query utama:

```powershell
.venv\Scripts\python.exe scripts/queries/read/query_produk_favorit_nosql.py
```

## Setup Project-1 dari Project-0

Restore dump Project-0 terlebih dahulu, lalu buat schema `p1_denorm` dari data tersebut:

```powershell
pg_restore -h 127.0.0.1 -p 5432 -U postgres --no-owner --no-privileges -d gayang sql/project_0_db.dump
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -v ON_ERROR_STOP=1 -f sql/project-1-denormalized.sql
```

`project-1-denormalized.sql` membaca tabel Project-0 di schema `public` dan membentuk aggregate di schema `p1_denorm`.

Setelah itu seed ke CouchDB dan Valkey:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --reset
```

Proses seed juga membuat counter agregat favorit di Valkey, sehingga query produk terfavorit tidak perlu memindai seluruh daftar favorit per pengguna.

## Cara menjalankan seed dan queries

```powershell
python scripts/seed/seed_nosql.py
python scripts/seed/seed_recent_gagal_kirim.py
python scripts/queries/dml/dml_5_8.py
python scripts/valkey/queries_valkey.py
python scripts/queries/read/query_produk_favorit_nosql.py
```