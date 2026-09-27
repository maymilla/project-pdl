# Project PDL

Project ini membandingkan pemrosesan data menggunakan PostgreSQL, CouchDB, dan Valkey. Data utama berasal dari database Project-0. Script seeding membaca tabel-tabel  tersebut secara langsung, lalu memindahkannya ke CouchDB (dokumen) dan Valkey.

Panduan ini menjelaskan setup dari awal sampai menjalankan query read dan DML.

## 1. Struktur Project

```text
project-pdl/
|-- compose.yml
|-- .env
|-- requirements.txt
|-- README.md
|-- couchdb-init/
|   |-- init.ps1              # buat database, Mango index, dan design doc views
|   |-- indexes.json
|   `-- views.json
|-- sql/
|   |-- project_0_db.dump
|   |-- project-1-denormalized.sql
|   `-- queries/
|       |-- read/
|       |   |-- query_7.sql
|       |   `-- query_8.sql
|       `-- dml/
|           |-- query_9.sql
|           |-- query_10.sql
|           |-- query_11.sql
|           `-- query_12.sql
|-- scripts/
|   |-- seed/
|   |   |-- seed_nosql.py
|   |   `-- seed_recent_gagal_kirim.py
|   |-- queries/
|   |   |-- read/query_7.py
|   |   |-- read/query_8.py
|   |   `-- dml/
|   |       |-- dml_5_8.py
|   |       |-- query_9.py
|   |       |-- query_10.py
|   |       |-- query_11.py
|   |       `-- query_12.py
|   `-- valkey/queries_valkey.py
`-- results/
    |-- read/query_7.txt
    |-- read/query_8.txt
    `-- dml/
        |-- dml_5_8_results.txt
        |-- query_9.txt
        |-- query_10.txt
        |-- query_11.txt
        `-- query_12.txt
```

## 2. Prasyarat

Pastikan aplikasi berikut sudah terpasang:

- PostgreSQL dan command line tools `psql` serta `pg_restore`.
- Docker Desktop.
- Python 3.13 atau versi kompatibel.
- Git, jika project diambil dari repository.

Project ini menggunakan:

- PostgreSQL sebagai sumber data Project-0.
- CouchDB sebagai penyimpanan dokumen.
- Valkey sebagai penyimpanan key-value, set, dan status.
- Python sebagai runner seeding dan query.

## 3. Masuk Ke Folder Project

Buka PowerShell, lalu masuk ke folder project:

```powershell
cd D:\project-pdl
```

Sesuaikan path tersebut jika folder project berada di lokasi lain.

## 4. Siapkan File `.env`

Buat atau buka file `.env` di root project:

```env
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DB=gayang
PG_USER=postgres
PG_PASSWORD=PASSWORD_POSTGRES_KAMU

COUCH_URL=http://127.0.0.1:5984
COUCH_DB=gayang
COUCH_USER=admin_gayang
COUCH_PASSWORD=gayang123

VALKEY_HOST=127.0.0.1
VALKEY_PORT=6379
VALKEY_DB=0
```

Ganti `PASSWORD_POSTGRES_KAMU` dengan password PostgreSQL lokal. Jangan commit `.env` atau membagikan password ke repository.

Buat database PostgreSQL `gayang` jika belum ada:

```powershell
psql -U postgres -c "CREATE DATABASE gayang;"
```

## 5. Buat Virtual Environment dan Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Isi utama `requirements.txt` adalah:

- `psycopg[binary]` untuk koneksi PostgreSQL.
- `requests` untuk koneksi CouchDB.
- `python-dotenv` untuk membaca `.env`.
- `valkey` untuk koneksi Valkey.

Semua command Python berikutnya dapat dijalankan dengan interpreter eksplisit, sehingga aktivasi environment tidak wajib:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Library utama: `psycopg[binary]`, `requests`, `python-dotenv`, `valkey`.

Semua perintah Python berikutnya memakai interpreter eksplisit `.venv\Scripts\python.exe`, sehingga aktivasi environment tidak wajib.

## 6. Restore Database Project-0

```powershell
pg_restore -h 127.0.0.1 -p 5432 -U postgres --no-owner --no-privileges -d gayang sql/project_0_db.dump
```

Cek tabel sumber:

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -c "\dt public.*"
```

Tabel yang dibaca oleh seeding: `pengguna`, `alamat`, `produk`, `kategori`, `produk_favorit`, `ulasan`, `pesanan`, `detail_pesanan`, `pembayaran`, `pengiriman`, `penyewaan`, `pengembalian`, `ruang_chat`, `pesan_chat`.

Restore dapat melaporkan konflik jika tabel sudah pernah direstore. Untuk setup bersih, gunakan database kosong.
## 7. Nyalakan CouchDB dan Valkey

Pastikan Docker Desktop running, lalu:

```powershell
docker compose up -d
docker compose ps
```

Container yang diharapkan berstatus Up:

```text
gayang-couchdb
gayang-valkey
```

Menghentikan / menyalakan kembali tanpa menghapus data:

```powershell
docker compose stop
docker compose start
```

Jangan menjalankan `docker compose down -v` sembarangan karena `-v` menghapus volume CouchDB dan Valkey.

### Cek CouchDB

Buka Fauxton di `http://127.0.0.1:5984/_utils/` dan login dengan `COUCH_USER` / `COUCH_PASSWORD`.

Pada volume baru, log CouchDB akan menampilkan error `database_does_not_exist ... _users` berulang kali. Ini karena CouchDB 3.x tidak membuat database sistem secara otomatis. Error tersebut tidak memengaruhi database `gayang`, tetapi bisa dihilangkan dengan membuat database sistem sekali saja:

```powershell
$h = @{ Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin_gayang:gayang123")) }
Invoke-RestMethod -Method Put -Uri http://127.0.0.1:5984/_users -Headers $h
Invoke-RestMethod -Method Put -Uri http://127.0.0.1:5984/_replicator -Headers $h
```

### Cek Valkey

```powershell
docker exec -it gayang-valkey valkey-cli PING
```

Output yang diharapkan: `PONG`.

## 8. Seeding CouchDB dan Valkey

```powershell
.venv\Scripts\python.exe scripts/seed/seed_nosql.py
```

Script ini tidak menerima opsi apa pun. Setiap kali dijalankan, script akan:

1. **Menghapus dan membuat ulang** database CouchDB `gayang` (semua index dan views ikut terhapus).
2. Memasukkan dokumen ke CouchDB dari tabel `public`.
3. Menambahkan set ke Valkey (`produk_favorit:*`, `produk_favorit_user:*`, `ruang_chat:*`).

Valkey **tidak** dikosongkan oleh script ini. Untuk mengembalikan Valkey ke kondisi awal (misalnya setelah menjalankan DML), kosongkan dulu sebelum seeding:

```powershell
docker exec -it gayang-valkey valkey-cli FLUSHDB
```

Tunggu sampai proses selesai. Jangan menutup terminal saat bulk insert masih berjalan.

### Dokumen yang dibuat di CouchDB

Setiap dokumen memiliki field `type` dan `_id` berformat `<type>:<id>`.

| `type` | `_id` | Isi tambahan | Jumlah |
|---|---|---|---|
| `pengguna` | `pengguna:{id}` | daftar `id_alamat` | 10000 |
| `produk` | `produk:{id}` | objek `kategori` | 20000 |
| `pesanan` | `pesanan:{id}` | `id_pembayaran`, `status_pesanan`, array `pengiriman` dan `detail_pesanan` | 50000 |
| `penyewaan` | `penyewaan:{id}` | objek `pengembalian` | 49975 |
| `pengembalian` | `pengembalian:{id}` | `status_pengembalian` | 16600 |
| `ruang_chat` | `ruang_chat:{id}` | `pesan_terakhir` | 9999 |
| `pesan_chat` | `pesan_chat:{id}` | | 100000 |
| `alamat` | `alamat:{id}` | | 20000 |
| `pembayaran` | `pembayaran:{id}` | `status_pembayaran` | 50000 |
| `ulasan` | `ulasan:{id}` | | 19999 |
| `detail_pesanan` | `detail_pesanan:{id_pesanan}:{no_urut}` | | 100000 |
| `pengiriman` | `pengiriman:{id}` | `status_pengiriman` | 50000 |
| **Total** | | | **496573** |

Output yang diharapkan di terminal:

```text
=== Reset CouchDB ===
Database belum ada            (atau: Database lama dihapus)
Database gayang dibuat ulang
Inserted 10000 documents
...
Inserted 50000 documents

=== Valkey: produk favorit ===
  Produk favorit + reverse index: 39998

=== Valkey: ruang chat ===
  Ruang chat: 9999

Valkey selesai.
```

### Key yang dibuat di Valkey

| Key | Tipe | Isi |
|---|---|---|
| `produk_favorit:{id_pengguna}` | set | id produk favorit pengguna |
| `produk_favorit_user:{id_produk}` | set | id pengguna yang memfavoritkan produk |
| `ruang_chat:{id_kecil}:{id_besar}` | set | id ruang chat antara dua pengguna |

Key `counter:{doctype}` dibuat saat runtime oleh DML yang membutuhkan ID baru (lihat `scripts/valkey/valkey_access.py`).

## 9. Verifikasi Seeding

Cek jumlah dokumen CouchDB:

```powershell
$h = @{ Authorization = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin_gayang:gayang123")) }
(Invoke-RestMethod -Uri http://127.0.0.1:5984/gayang -Headers $h).doc_count
```

Hasil yang diharapkan: `496573` tepat setelah seeding. Setelah `init.ps1` dijalankan, angka ini bertambah sesuai jumlah design doc index/views.

`_bulk_docs` mengembalikan HTTP 201 walaupun ada dokumen yang gagal, jadi pesan `Inserted N documents` bukan jaminan. Cek jumlah ini untuk memastikan.

Cek Valkey:

```powershell
docker exec -it gayang-valkey valkey-cli DBSIZE
docker exec -it gayang-valkey valkey-cli SCAN 0 MATCH "produk_favorit:*" COUNT 100
docker exec -it gayang-valkey valkey-cli SCAN 0 MATCH "ruang_chat:*" COUNT 100
```

## 10. Tambahkan Index dan View CouchDB

Jalankan **setelah** seeding selesai, dari dalam folder `couchdb-init` (script membaca `indexes.json` dan `views.json` dengan path relatif):

```powershell
cd couchdb-init
./init.ps1
cd ..
```

Script membuat Mango index dari `indexes.json` dan design doc `_design/views` dari `views.json` (`pendapatan_per_kategori`, `detail_by_produk`, `penyewaan_by_user_produk`, `pengiriman_gagal`, `rating_per_produk`, `produk_by_id`, `transaksi_per_user`, `stats_by_metode`).

Kredensial diambil dari environment variable `COUCH_USER` / `COUCH_PASSWORD` jika ada, dan jika tidak ada memakai default `admin_gayang` / `gayang123`. Script **tidak** membaca file `.env`.

Karena `seed_nosql.py` menghapus database `gayang`, **jalankan ulang `init.ps1` setiap selesai seeding**. Query read 8-11 bergantung pada views ini dan akan kosong tanpanya. Jalankan ulang juga setiap kali `indexes.json` atau `views.json` diubah.

## 11. Menjalankan Query Read

| Query | Deskripsi | Sumber data |
|---|---|---|
| 1 | Tren pendapatan bulanan per kategori | view `pendapatan_per_kategori` + dokumen produk |
| 2 | Top 10 pembeli berdasarkan total belanja dan jumlah ulasan | pembayaran berhasil + pesanan + ulasan per pengguna |
| 3 | Pengguna yang menyewa produk sama lebih dari sekali | view `penyewaan_by_user_produk` |
| 4 | Top 20 penjual berdasarkan pendapatan pembelian selesai | pembayaran berhasil + detail pembelian pada pesanan selesai |
| 5 | Produk paling sering disewa beserta jumlah ulasan dan rating | view `penyewaan_per_detail` + `rating_per_produk` |
| 6 | Penyewaan terlambat beserta status pengembalian | view `penyewaan_terlambat` + dokumen pesanan/pengguna/produk |
| 7 | Produk yang paling sering difavoritkan beserta penjualnya | Valkey `produk_favorit_user:*` + CouchDB |
| 8 | Metode pembayaran terbanyak beserta jumlah transaksi berhasil dan total nominal | view `stats_by_metode` |
| 9 | 10 produk dengan rating di atas rata-rata, beserta jumlah ulasan dan kategori | view `rating_per_produk` |
| 10 | Pengguna dengan transaksi pembelian dan penyewaan terbanyak | view `transaksi_per_user` |
| 11 | Produk yang belum pernah diulas | views `rating_per_produk`, `produk_by_id` |
| 12 | Riwayat transaksi lengkap pengguna | Mango `_find` pada `pesanan` |

```powershell
.venv\Scripts\python.exe scripts/queries/read/query_1.py
.venv\Scripts\python.exe scripts/queries/read/query_2.py
.venv\Scripts\python.exe scripts/queries/read/query_3.py
.venv\Scripts\python.exe scripts/queries/read/query_4.py
.venv\Scripts\python.exe scripts/queries/read/query_5.py
.venv\Scripts\python.exe scripts/queries/read/query_6.py
.venv\Scripts\python.exe scripts/queries/read/query_7.py
.venv\Scripts\python.exe scripts/queries/read/query_8.py
.venv\Scripts\python.exe scripts/queries/read/query_9.py
.venv\Scripts\python.exe scripts/queries/read/query_10.py
.venv\Scripts\python.exe scripts/queries/read/query_11.py
.venv\Scripts\python.exe scripts/queries/read/query_12.py
```

Versi SQL pembanding ada di `sql/queries/read/`.

## 12. Menjalankan Query DML

DML mengubah data di CouchDB dan Valkey. Untuk kembali ke snapshot awal, lihat bagian 14.

### DML 1-4

Script ini mengimpor `scripts.queries.utils`, jadi harus dijalankan sebagai modul (`-m`) dari root project:

```powershell
.venv\Scripts\python.exe -m scripts.queries.dml.query_1   # insert pesanan baru
.venv\Scripts\python.exe -m scripts.queries.dml.query_2   # update status produk menjadi terjual
.venv\Scripts\python.exe -m scripts.queries.dml.query_3   # hapus favorit untuk produk nonaktif/terjual
.venv\Scripts\python.exe -m scripts.queries.dml.query_4   # insert ulasan untuk pesanan selesai
```

### DML 5-8

Jika butuh data `gagal_kirim` terbaru untuk Query 5 dan 6, tambahkan data test terlebih dahulu (langsung ke CouchDB dan Valkey, bukan PostgreSQL; aman dijalankan ulang):

```powershell
.venv\Scripts\python.exe scripts/seed/seed_recent_gagal_kirim.py
```

```powershell
.venv\Scripts\python.exe scripts/queries/dml/query_5.py   # insert pengiriman ulang untuk gagal kirim
.venv\Scripts\python.exe scripts/queries/dml/query_6.py   # batalkan pesanan + refund (gagal kirim > 7 hari)
.venv\Scripts\python.exe scripts/queries/dml/query_7.py   # insert pesan + ruang chat baru
.venv\Scripts\python.exe scripts/queries/dml/query_8.py   # update pengiriman saat diserahkan ke kurir
```

### DML 9-12

```powershell
.venv\Scripts\python.exe scripts/queries/dml/query_9.py                        # batalkan pesanan lewat batas bayar (--batas-jam, default 24)
.venv\Scripts\python.exe scripts/queries/dml/query_10.py --id-pengembalian 1   # penyewaan -> selesai
.venv\Scripts\python.exe scripts/queries/dml/query_11.py --id-penyewaan 1      # produk -> disewa
.venv\Scripts\python.exe scripts/queries/dml/query_12.py --id-produk 1756      # produk -> tersedia
```

Keempatnya menerima `--dry-run` untuk menampilkan kandidat tanpa menulis ke Valkey.

> **Known issue:** Query 9-12 membaca dan menulis status di key Valkey `status:<entitas>:<id>` (misalnya `status:pesanan:1`). Seeding saat ini tidak membuat key tersebut, karena status disimpan di dokumen CouchDB (`status_pesanan`, `status_pembayaran`, `status_pengembalian`, dan seterusnya). Akibatnya Query 9-12 tidak akan menemukan kandidat sampai script-nya diubah untuk membaca status dari CouchDB, atau seeding diubah untuk mengisi key `status:*`.

Versi SQL pembanding ada di `sql/queries/dml/`.

## 13. Lokasi Hasil

Semua script query menulis output ke:

```text
results/read/query_<n>.txt
results/dml/query_<n>.txt
```

Folder dibuat otomatis jika belum ada.

## 14. Urutan Lengkap Dari Awal

```powershell
cd D:\project-pdl

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

pg_restore -h 127.0.0.1 -p 5432 -U postgres --no-owner --no-privileges -d gayang sql/project_0_db.dump

docker compose up -d
docker compose ps

.venv\Scripts\python.exe scripts/seed/seed_nosql.py

cd couchdb-init
./init.ps1
cd ..

.venv\Scripts\python.exe scripts/queries/read/query_7.py
.venv\Scripts\python.exe scripts/queries/read/query_8.py
.venv\Scripts\python.exe scripts/queries/read/query_9.py
.venv\Scripts\python.exe scripts/queries/read/query_10.py
.venv\Scripts\python.exe scripts/queries/read/query_11.py
.venv\Scripts\python.exe scripts/queries/read/query_12.py

.venv\Scripts\python.exe -m scripts.queries.dml.query_1
.venv\Scripts\python.exe -m scripts.queries.dml.query_2
.venv\Scripts\python.exe -m scripts.queries.dml.query_3
.venv\Scripts\python.exe -m scripts.queries.dml.query_4
.venv\Scripts\python.exe scripts/seed/seed_recent_gagal_kirim.py
.venv\Scripts\python.exe scripts/queries/dml/query_5.py
.venv\Scripts\python.exe scripts/queries/dml/query_6.py
.venv\Scripts\python.exe scripts/queries/dml/query_7.py
.venv\Scripts\python.exe scripts/queries/dml/query_8.py
.venv\Scripts\python.exe scripts/queries/dml/query_9.py
.venv\Scripts\python.exe scripts/queries/dml/query_10.py --id-pengembalian 1
.venv\Scripts\python.exe scripts/queries/dml/query_11.py --id-penyewaan 1
.venv\Scripts\python.exe scripts/queries/dml/query_12.py --id-produk 1756
```

### Kembali ke snapshot awal

Setelah menjalankan DML, kembalikan CouchDB dan Valkey ke kondisi awal dengan:

```powershell
docker exec -it gayang-valkey valkey-cli FLUSHDB
.venv\Scripts\python.exe scripts/seed/seed_nosql.py
cd couchdb-init; ./init.ps1; cd ..
```

## 15. Saat Membuka Project Lagi

Jika volume Docker masih ada, tidak perlu restore atau seed ulang:

```powershell
cd D:\project-pdl
docker compose up -d
.\.venv\Scripts\Activate.ps1
```

Jangan menjalankan `seed_nosql.py` hanya untuk mengecek data, karena script tersebut selalu menghapus dan membuat ulang CouchDB. Gunakan pengecekan di bagian 9.

## 16. Troubleshooting Singkat

### `Connection refused` ke Valkey atau CouchDB

```powershell
docker compose up -d
docker compose ps
```

### Log CouchDB penuh error `_users database does not exist`

Buat database sistem `_users` dan `_replicator` (lihat bagian 7). Error ini tidak memengaruhi seeding maupun query.

### Query read 8-11 kosong atau error `not_found`

Design doc views belum ada, biasanya karena seeding dijalankan ulang setelah `init.ps1`. Jalankan ulang `couchdb-init/init.ps1`.

### `ModuleNotFoundError: No module named 'scripts'`

Terjadi pada DML 1-4 jika dijalankan dengan path file. Jalankan dari root project dengan `python -m scripts.queries.dml.query_<n>`.

### CouchDB atau Valkey berisi data lama

Ikuti langkah "Kembali ke snapshot awal" di bagian 14.

### Password PostgreSQL gagal

Periksa `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, dan `PG_PASSWORD` di `.env`.
