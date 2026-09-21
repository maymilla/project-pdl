-- Self-contained Project-1 dataset.
-- This file does not depend on Project-0 tables.

BEGIN;

DROP SCHEMA IF EXISTS p1_denorm CASCADE;
CREATE SCHEMA p1_denorm;

CREATE TABLE p1_denorm.pengguna (
    id_pengguna bigint PRIMARY KEY,
    nama text NOT NULL,
    email text NOT NULL,
    no_telp text,
    password_hash text,
    tanggal_daftar timestamptz,
    alamat jsonb NOT NULL DEFAULT '[]'::jsonb
);

INSERT INTO p1_denorm.pengguna
    (id_pengguna, nama, email, no_telp, password_hash, tanggal_daftar, alamat)
VALUES
    (1, 'Alya Pratama', 'alya@example.com', '0811000001', 'demo-hash-1', '2026-01-10', '[]'),
    (2, 'Bima Santoso', 'bima@example.com', '0811000002', 'demo-hash-2', '2026-01-11', '[]'),
    (3, 'Citra Lestari', 'citra@example.com', '0811000003', 'demo-hash-3', '2026-01-12', '[]'),
    (4, 'Dimas Wijaya', 'dimas@example.com', '0811000004', 'demo-hash-4', '2026-01-13', '[]');

CREATE TABLE p1_denorm.produk (
    id_produk bigint PRIMARY KEY,
    id_penjual bigint NOT NULL,
    nama_produk text NOT NULL,
    deskripsi text,
    ukuran text,
    kondisi text,
    harga_jual numeric,
    harga_sewa numeric,
    status_produk text,
    tanggal_dibuat timestamptz,
    kategori jsonb
);

INSERT INTO p1_denorm.produk
    (id_produk, id_penjual, nama_produk, deskripsi, ukuran, kondisi, harga_jual, harga_sewa, status_produk, tanggal_dibuat, kategori)
VALUES
    (1, 1, 'Kamera Mirrorless', 'Kamera ringan untuk perjalanan.', 'One size', 'bekas baik', 8500000, 250000, 'tersedia', '2026-02-01', '{"id_kategori": 1, "nama_kategori": "Elektronik"}'),
    (2, 1, 'Tripod Carbon', 'Tripod kokoh dan ringan.', '150 cm', 'bekas baik', 1200000, 75000, 'tersedia', '2026-02-02', '{"id_kategori": 1, "nama_kategori": "Elektronik"}'),
    (3, 2, 'Tas Kamera Outdoor', 'Tas kamera tahan air.', '20 liter', 'baru', 950000, 50000, 'tersedia', '2026-02-03', '{"id_kategori": 2, "nama_kategori": "Aksesori"}'),
    (4, 2, 'Lampu Studio LED', 'Lampu LED untuk studio kecil.', '60 watt', 'bekas baik', 1750000, 100000, 'tersedia', '2026-02-04', '{"id_kategori": 1, "nama_kategori": "Elektronik"}'),
    (5, 1, 'Mic Wireless', 'Mikrofon wireless untuk konten.', 'One size', 'baru', 2100000, 150000, 'tersedia', '2026-02-05', '{"id_kategori": 3, "nama_kategori": "Audio"}');

CREATE TABLE p1_denorm.ulasan (
    id_ulasan bigint PRIMARY KEY,
    id_produk bigint NOT NULL,
    id_pengguna bigint NOT NULL,
    rating integer,
    komentar text,
    tanggal_ulasan timestamptz
);

INSERT INTO p1_denorm.ulasan
    (id_ulasan, id_produk, id_pengguna, rating, komentar, tanggal_ulasan)
VALUES
    (1, 3, 1, 5, 'Tasnya praktis dan kuat.', '2026-03-01'),
    (2, 1, 3, 4, 'Kondisi sesuai deskripsi.', '2026-03-02');

CREATE TABLE p1_denorm.pesanan (
    id_pesanan bigint PRIMARY KEY,
    id_penjual bigint,
    id_pembeli bigint,
    id_alamat bigint,
    tanggal_pesanan timestamptz,
    status_pesanan text,
    total_pesanan numeric,
    pembayaran jsonb,
    pengiriman jsonb NOT NULL DEFAULT '[]'::jsonb,
    detail_pesanan jsonb NOT NULL DEFAULT '[]'::jsonb
);

INSERT INTO p1_denorm.pesanan
    (id_pesanan, id_penjual, id_pembeli, id_alamat, tanggal_pesanan, status_pesanan, total_pesanan, pembayaran, pengiriman, detail_pesanan)
VALUES
    (1, 2, 1, NULL, '2026-03-05', 'selesai', 950000,
     '{"id_pembayaran": 1, "metode_pembayaran": "transfer", "nominal": 950000, "status_pembayaran": "berhasil"}',
     '[{"id_pengiriman": 1, "kurir": "JNE", "no_resi": "JNE001", "tanggal_kirim": "2026-03-06", "status_pengiriman": "dikirim", "tanggal_terima": null}]',
     '[{"id_detail": 1, "no_urut": 1, "id_produk": 3, "jenis_transaksi": "beli", "harga": 950000}]');

CREATE TABLE p1_denorm.ruang_chat (
    id_ruang_chat bigint PRIMARY KEY,
    id_penjual bigint NOT NULL,
    id_pembeli bigint NOT NULL,
    pesan_chat jsonb NOT NULL DEFAULT '[]'::jsonb
);

INSERT INTO p1_denorm.ruang_chat
    (id_ruang_chat, id_penjual, id_pembeli, pesan_chat)
VALUES
    (1, 2, 1, '[{"id_pesan": 1, "id_pengirim": 1, "pesan": "Apakah masih tersedia?", "waktu_kirim": "2026-03-04T10:00:00Z", "status": "terkirim"}]');

CREATE TABLE p1_denorm.produk_favorit_user (
    id_pengguna bigint PRIMARY KEY,
    id_produk bigint[] NOT NULL
);

INSERT INTO p1_denorm.produk_favorit_user (id_pengguna, id_produk)
VALUES
    (1, ARRAY[1, 2, 3]::bigint[]),
    (2, ARRAY[1, 3, 4]::bigint[]),
    (3, ARRAY[1, 3, 5]::bigint[]),
    (4, ARRAY[3, 4, 5]::bigint[]);

CREATE TABLE p1_denorm.ruang_chat_user (
    id_pengguna bigint PRIMARY KEY,
    id_ruang_chat bigint[] NOT NULL
);

INSERT INTO p1_denorm.ruang_chat_user (id_pengguna, id_ruang_chat)
VALUES
    (1, ARRAY[1]::bigint[]),
    (2, ARRAY[1]::bigint[]),
    (3, ARRAY[]::bigint[]),
    (4, ARRAY[]::bigint[]);

CREATE VIEW p1_denorm.valkey_favorit_export AS
SELECT
    pengguna.id_pengguna,
    favorit.id_produk
FROM p1_denorm.produk_favorit_user AS pengguna
CROSS JOIN LATERAL unnest(pengguna.id_produk) AS favorit(id_produk);

CREATE VIEW p1_denorm.valkey_ruang_chat_export AS
SELECT id_penjual AS id_pengguna, id_ruang_chat
FROM p1_denorm.ruang_chat
UNION
SELECT id_pembeli AS id_pengguna, id_ruang_chat
FROM p1_denorm.ruang_chat;

CREATE VIEW p1_denorm.valkey_status_export AS
SELECT 'status:produk:' || id_produk::text AS key, status_produk AS value
FROM p1_denorm.produk
UNION ALL
SELECT 'status:pesanan:' || id_pesanan::text, status_pesanan
FROM p1_denorm.pesanan;

COMMIT;