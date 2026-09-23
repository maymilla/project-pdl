# Project PDL

Project ini membandingkan pemrosesan data menggunakan PostgreSQL, CouchDB, dan Valkey. Data utama berasal dari database Project-0, lalu dibentuk menjadi schema PostgreSQL denormalisasi `p1_denorm` sebelum dipindahkan ke CouchDB dan Valkey.

Panduan ini menjelaskan setup dari awal sampai menjalankan query dan eksperimen DML.

## 1. Struktur Project

```text
project-pdl/
|-- compose.yml
|-- .env
|-- requirements.txt
|-- README.md
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

Buat atau buka file `.env` di root project. Gunakan format berikut:

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

Database PostgreSQL yang digunakan project ini adalah `gayang`. Jika database tersebut belum ada, buat terlebih dahulu:

```powershell
psql -U postgres -c "CREATE DATABASE gayang;"
```

Jika database sudah ada, perintah tersebut tidak perlu dijalankan.

## 5. Buat Virtual Environment Python

Buat virtual environment dari root project:

```powershell
python -m venv .venv
```

Aktifkan virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Jika PowerShell menolak aktivasi karena execution policy, jalankan PowerShell sebagai user biasa dengan perintah berikut, lalu ulangi aktivasi:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Setelah aktif, prompt biasanya memiliki prefix `(.venv)`.

## 6. Install Dependencies

Install semua library yang digunakan project:

```powershell
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
.venv\Scripts\python.exe --version
```

## 7. Pastikan Project-0 Tersedia

Project ini membutuhkan data Project-0. File dump yang disediakan berada di:

```text
sql/project_0_db.dump
```

Dump tersebut berisi tabel Project-0 pada schema `public`, termasuk tabel seperti:

- `pengguna`
- `produk`
- `produk_favorit`
- `ulasan`
- `pesanan`
- `pembayaran`
- `pengiriman`
- `detail_pesanan`
- `ruang_chat`

## 8. Restore Database Project-0

Restore dump ke database `gayang`:

```powershell
pg_restore -h 127.0.0.1 -p 5432 -U postgres --no-owner --no-privileges -d gayang sql/project_0_db.dump
```

Masukkan password PostgreSQL ketika diminta.

Untuk memastikan tabel sumber sudah tersedia:

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -c "\dt public.*"
```

Cek jumlah beberapa tabel sumber:

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -c "SELECT COUNT(*) AS pengguna FROM public.pengguna; SELECT COUNT(*) AS produk FROM public.produk; SELECT COUNT(*) AS pesanan FROM public.pesanan;"
```

Restore dump dapat melaporkan konflik jika tabel Project-0 sudah pernah direstore. Untuk setup yang benar-benar bersih, gunakan database kosong atau hapus database target terlebih dahulu sesuai prosedur PostgreSQL yang digunakan.

## 9. Buat Schema Denormalisasi

Jalankan script berikut setelah tabel Project-0 tersedia:

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -v ON_ERROR_STOP=1 -f sql/project-1-denormalized.sql
```

Script ini:

- Tidak mengubah tabel sumber Project-0 di schema `public`.
- Menghapus dan membuat ulang schema `p1_denorm`.
- Menggabungkan data terkait menjadi JSONB atau array.
- Membuat view export untuk kebutuhan seeding Valkey.

Periksa hasil denormalisasi:

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema = 'p1_denorm' ORDER BY table_name;"
```

Cek jumlah root table:

```sql
SELECT 'pengguna' AS tabel, COUNT(*) AS jumlah FROM p1_denorm.pengguna
UNION ALL
SELECT 'produk', COUNT(*) FROM p1_denorm.produk
UNION ALL
SELECT 'ulasan', COUNT(*) FROM p1_denorm.ulasan
UNION ALL
SELECT 'pesanan', COUNT(*) FROM p1_denorm.pesanan
UNION ALL
SELECT 'ruang_chat', COUNT(*) FROM p1_denorm.ruang_chat;
```

Dengan dump yang digunakan di project ini, jumlahnya adalah:

```text
pengguna   10000
produk     20000
ulasan     19999
pesanan    50000
ruang_chat 9999
```

Contoh untuk melihat data embedded:

```sql
SELECT id_pengguna, nama, jsonb_pretty(alamat)
FROM p1_denorm.pengguna
LIMIT 3;

SELECT
    id_pesanan,
    jsonb_pretty(pembayaran),
    jsonb_pretty(pengiriman),
    jsonb_pretty(detail_pesanan)
FROM p1_denorm.pesanan
LIMIT 1;
```

## 10. Nyalakan CouchDB dan Valkey

Pastikan Docker Desktop sudah running, lalu jalankan dari root project:

```powershell
docker compose up -d
```

Periksa status container:

```powershell
docker compose ps
docker ps
```

Container yang diharapkan:

```text
gayang-couchdb
gayang-valkey
```

Keduanya harus berstatus running atau Up.

Untuk menghentikan container tanpa menghapus data volume:

```powershell
docker compose stop
```

Untuk menyalakan kembali container:

```powershell
docker compose start
```

Jangan menjalankan perintah berikut sembarangan karena `-v` menghapus volume CouchDB dan Valkey:

```powershell
docker compose down -v
```

## 11. Cek CouchDB

Buka Fauxton di browser:

```text
http://127.0.0.1:5984/_utils/
```

Login menggunakan nilai dari `.env`:

```text
username: admin_gayang
password: sesuai COUCH_PASSWORD
```

Atau cek endpoint CouchDB dari PowerShell:

```powershell
Invoke-WebRequest http://127.0.0.1:5984/ | Select-Object -ExpandProperty Content
```

Database `gayang` akan dibuat oleh script seeding jika belum tersedia

## 12. Cek Valkey

Gunakan Valkey CLI di dalam container:

```powershell
docker exec -it gayang-valkey valkey-cli
```

Tes koneksi:

```text
PING
```

Output yang diharapkan:

```text
PONG
```

Keluar dari CLI:

```text
exit
```

## 13. Test Seeding Dengan Data Kecil

Sebelum full seeding, jalankan test kecil:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --limit 5 --reset
```

Arti opsi:

- `--limit 5` membatasi jumlah baris yang diambil dari setiap sumber.
- `--reset` menghapus dan membuat ulang database CouchDB serta menjalankan `FLUSHDB` pada Valkey.
- PostgreSQL tidak dihapus atau diubah oleh `--reset`.

Output awal yang diharapkan:

```text
PostgreSQL pengguna: 10000
CouchDB user: admin_gayang
Valkey: True
p1_denorm: OK
```

Jika test selesai, periksa contoh dokumen di CouchDB melalui Fauxton. Contoh ID:

```text
pengguna:1
produk:1
pesanan:1
ruang_chat:1
```

Periksa key Valkey:

```powershell
docker exec -it gayang-valkey valkey-cli SCAN 0 MATCH "status:*" COUNT 100
docker exec -it gayang-valkey valkey-cli GET status:produk:1
docker exec -it gayang-valkey valkey-cli SCAN 0 MATCH "produk_favorit:*" COUNT 100
docker exec -it gayang-valkey valkey-cli SCAN 0 MATCH "ruang_chat:*" COUNT 100
```

## 14. Full Seeding

Jika test kecil sudah berhasil, jalankan full seed:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --reset
```

Full seed memindahkan:

- Dokumen pengguna ke CouchDB.
- Dokumen produk ke CouchDB.
- Dokumen ulasan ke CouchDB.
- Dokumen pesanan ke CouchDB.
- Dokumen ruang chat ke CouchDB.
- Status, favorit, dan membership ruang chat ke Valkey.

Tunggu sampai proses selesai. Jangan menutup terminal saat bulk insert masih berjalan.

## 15. Verifikasi Full Seeding

Jalankan verifikasi tanpa melakukan seeding ulang:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --verify-only
```

Dengan data project saat ini, verifikasi CouchDB seharusnya menunjukkan:

```text
expected root docs : 109998
actual doc_count   : 109998
[OK] Jumlah root document cocok.
```

Angka `109998` berasal dari:

```text
10000 pengguna
20000 produk
19999 ulasan
50000 pesanan
9999 ruang_chat
= 109998 root documents
```

Verifikasi juga menampilkan jumlah key Valkey dan beberapa contoh dokumen serta status.

### Tambahkan Index dan View CouchDB

Setelah CouchDB berjalan, jalankan script PowerShell berikut dari root project untuk menambahkan database `gayang`, Mango index dari `couchdb-init/indexes.json`, dan view dari `couchdb-init/views.json`:

```powershell
cd couchdb-init
./init.ps1
```

Script membaca `COUCH_USER` dan `COUCH_PASSWORD` dari file `.env` di folder induk, lalu menunggu CouchDB siap sebelum membuat index dan view.

Jalankan ulang script tersebut setiap kali file index atau view di folder `couchdb-init` diubah.

## 16. Menjalankan Query Read

Query 7 mencari semua produk yang memiliki jumlah favorit maksimum, beserta penjualnya:

```powershell
.venv\Scripts\python.exe scripts/queries/read/query_7.py
```

Query 8 mencari semua metode pembayaran dengan jumlah transaksi berhasil maksimum. Query ini membaca pembayaran dari CouchDB dan status pembayaran dari Valkey saat runtime:

```powershell
.venv\Scripts\python.exe scripts/queries/read/query_8.py
```

Kedua query tersebut memang menghitung saat runtime agar perbandingan dengan query SQL tetap adil. Query tidak menggunakan aggregate hasil yang sudah dihitung sebelumnya.

## 17. Menjalankan Query Valkey

Untuk mencoba operasi favorit, membership ruang chat, dan status di Valkey:

```powershell
.venv\Scripts\python.exe scripts/valkey/queries_valkey.py
```

## 18. Menjalankan DML 5-8

Jika membutuhkan target `gagal_kirim` terbaru untuk pengujian Query 5 dan 6, tambahkan data test terlebih dahulu:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_recent_gagal_kirim.py
```

Script ini menambahkan data langsung ke CouchDB dan Valkey, bukan ke PostgreSQL.

Jalankan eksperimen DML:

```powershell
.venv\Scripts\python.exe scripts/queries/dml/dml_5_8.py
```

Script tersebut menjalankan Query 5 sampai 8, membuat index CouchDB yang diperlukan, melakukan warm-up, lalu membandingkan pengukuran sebelum dan sesudah index. Hasilnya disimpan di:

```text
results/dml/dml_5_8_results.txt
```

DML dapat mengubah data/status di CouchDB dan Valkey. Jika ingin kembali ke snapshot awal yang sama dengan PostgreSQL, jalankan ulang:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --reset
```

### Menjalankan DML 9-12

Query 9 membatalkan pesanan yang melewati batas waktu pembayaran (default 24 jam) dan belum punya pembayaran berhasil. Status pesanan dan pembayaran dibaca/ditulis di Valkey (`status:pesanan:{id}`, `status:pembayaran:{id}`):

```powershell
.venv\Scripts\python.exe scripts/queries/dml/query_9.py
```

Query 10 menandai penyewaan selesai setelah pengembaliannya berstatus selesai (default `id_pengembalian=1`). Penyewaan terkait dicari lewat dokumen `pesanan.detail_pesanan[].penyewaan.pengembalian` di CouchDB, status ditulis ke `status:penyewaan:{id}`:

```powershell
.venv\Scripts\python.exe scripts/queries/dml/query_10.py --id-pengembalian 1
```

Query 11 menandai produk sedang disewa saat penyewaannya mulai berjalan (default `id_penyewaan=1`), menulis ke `status:produk:{id}`:

```powershell
.venv\Scripts\python.exe scripts/queries/dml/query_11.py --id-penyewaan 1
```

Query 12 mengembalikan status produk menjadi tersedia setelah ada pengembalian yang selesai untuk produk tersebut (default `id_produk=1756`):

```powershell
.venv\Scripts\python.exe scripts/queries/dml/query_12.py --id-produk 1756
```

Keempatnya menerima flag `--dry-run` untuk hanya menampilkan kandidat tanpa menulis ke Valkey. Sama seperti Query 5-8, jalankan ulang `seed_nosql.py --reset` jika ingin mengembalikan data ke snapshot awal.

## 19. Lokasi Hasil

Output query read disimpan di:

```text
results/read/query_7.txt
results/read/query_8.txt
```

Output eksperimen DML disimpan di:

```text
results/dml/dml_5_8_results.txt
results/dml/query_9.txt
results/dml/query_10.txt
results/dml/query_11.txt
results/dml/query_12.txt
```

## 20. Urutan Lengkap Dari Awal

Berikut urutan ringkas dari kondisi awal:

```powershell
cd D:\project-pdl

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

pg_restore -h 127.0.0.1 -p 5432 -U postgres --no-owner --no-privileges -d gayang sql/project_0_db.dump
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -v ON_ERROR_STOP=1 -f sql/project-1-denormalized.sql

docker compose up -d
docker compose ps

.venv\Scripts\python.exe scripts/seed/seed_nosql.py --limit 5 --reset
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --reset
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --verify-only

.venv\Scripts\python.exe scripts/queries/read/query_7.py
.venv\Scripts\python.exe scripts/queries/read/query_8.py
.venv\Scripts\python.exe scripts/valkey/queries_valkey.py
.venv\Scripts\python.exe scripts/queries/dml/dml_5_8.py
.venv\Scripts\python.exe scripts/queries/dml/query_9.py
.venv\Scripts\python.exe scripts/queries/dml/query_10.py --id-pengembalian 1
.venv\Scripts\python.exe scripts/queries/dml/query_11.py --id-penyewaan 1
.venv\Scripts\python.exe scripts/queries/dml/query_12.py --id-produk 1756
```

## 21. Saat Membuka Project Lagi

Jika database dan volume Docker masih ada, tidak perlu restore dan seed ulang setiap kali membuka laptop. Cukup:

```powershell
cd D:\project-pdl
docker compose up -d
.\.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --verify-only
```

Gunakan `--reset` hanya jika ingin membangun ulang CouchDB dan Valkey dari PostgreSQL atau menghapus data hasil testing sebelumnya.

## 22. Troubleshooting Singkat

### `Connection refused` ke Valkey atau CouchDB

Pastikan Docker hidup dan container berjalan:

```powershell
docker compose up -d
docker compose ps
```

### `Schema p1_denorm belum ditemukan`

Jalankan ulang denormalisasi:

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d gayang -v ON_ERROR_STOP=1 -f sql/project-1-denormalized.sql
```

### CouchDB atau Valkey berisi data lama

Gunakan reset saat seeding:

```powershell
.venv\Scripts\python.exe scripts/seed/seed_nosql.py --reset
```

### Log tidak bisa disimpan

Pastikan command dijalankan dari root project dan folder `results` tersedia. Script query akan membuat subfolder output yang diperlukan.

### Password PostgreSQL gagal

Periksa `PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, dan `PG_PASSWORD` di `.env`. Jangan menaruh password langsung di README atau command yang akan disimpan di history.
