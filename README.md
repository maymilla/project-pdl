# Project PDL

Project ini berisi eksperimen perbandingan PostgreSQL denormalisasi, CouchDB, dan Valkey. Data utama berasal dari dump Project-0, lalu dibentuk menjadi schema `p1_denorm` sebelum dipindahkan ke layanan NoSQL.

## Struktur Utama

```text
sql/
  project_0_db.dump
  project-1-denormalized.sql
  queries/read/query_7.sql
scripts/
  seed/seed_nosql.py
  seed/seed_recent_gagal_kirim.py
  queries/read/query_7.py
  queries/dml/dml_5_8.py
  valkey/queries_valkey.py
results/
  dml_5_8_results.txt
  produk_favorit_nosql_results.txt
```

## Prasyarat

- PostgreSQL aktif dan database `gayang` tersedia.
- Docker Desktop aktif.
- Virtual environment `.venv` sudah memiliki dependencies dari `requirements.txt`.
- File `.env` berisi koneksi PostgreSQL, CouchDB, dan Valkey.

## Setup Dari Project-0

Restore database Project-0, lalu bentuk schema denormalisasi `p1_denorm`:

```powershell
pg_restore -h 127.0.0.1 -p 5432 -U postgres --no-owner --no-privileges -d gayang sql/project_0_db.dump
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -v ON_ERROR_STOP=1 -f sql/project-1-denormalized.sql
```

Script denormalisasi membaca tabel Project-0 dari schema `public` dan membuat aggregate di schema `p1_denorm`.

## Menyalakan Layanan

```powershell
docker compose up -d
docker compose ps
```

## Seed Ke NoSQL

Seed data dari PostgreSQL ke CouchDB dan Valkey:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --reset
```

Gunakan `--reset` saat ingin membangun ulang database CouchDB dan Valkey dari awal. Proses seed juga membuat counter favorit agregat di Valkey agar query favorit tidak perlu memindai setiap daftar favorit pengguna.

Untuk menambahkan data pesanan uji dengan pengiriman gagal terbaru sebelum menjalankan DML:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_recent_gagal_kirim.py
```

## Menjalankan Query

Query produk paling sering difavoritkan, mengembalikan semua produk dengan jumlah favorit maksimum:

```powershell
.venv\Scripts\python.exe scripts/queries/read/query_7.py
```

Query dan operasi Valkey:

```powershell
.venv\Scripts\python.exe scripts/valkey/queries_valkey.py
```

Query DML 5-8 pada CouchDB dan Valkey:

```powershell
.venv\Scripts\python.exe scripts/queries/dml/dml_5_8.py
```

Script DML membuat index, menjalankan warm-up, mengukur query sebelum dan sesudah index, lalu menyimpan log hasil.

## Urutan Lengkap Eksperimen

```powershell
docker compose up -d
pg_restore -h 127.0.0.1 -p 5432 -U postgres --no-owner --no-privileges -d gayang sql/project_0_db.dump
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -v ON_ERROR_STOP=1 -f sql/project-1-denormalized.sql
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --reset
.venv\Scripts\python.exe scripts/queries/read/query_produk_favorit_nosql.py
.venv\Scripts\python.exe scripts/queries/read/query_7.py
.venv\Scripts\python.exe scripts/queries/dml/dml_5_8.py
```

## Hasil

Output runtime disimpan di folder `results/`:

- `read/query_7.txt`: hasil query produk favorit.
- `dml/dml_5_8_results.txt`: log pengukuran DML 5-8.