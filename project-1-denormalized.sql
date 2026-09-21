-- Project-1 IF4040 - Denormalized PostgreSQL baseline
-- Source: Project-0 normalized schema
-- Purpose:
--   1) Keep Project-0 tables unchanged as source-of-truth.
--   2) Create a separate denormalized schema for fairer SQL-vs-NoSQL comparison.
--   3) Prepare data that is easy to migrate to CouchDB and Valkey.
--
-- IMPORTANT:
--   - This script DOES NOT create CouchDB design docs/indexes.
--   - This script DOES NOT create secondary PostgreSQL performance indexes.
--   - Primary keys are added only to preserve row identity/integrity.
--   - Run this AFTER project-0.sql + seed.sql have populated PostgreSQL.

BEGIN;

DROP SCHEMA IF EXISTS p1_denorm CASCADE;
CREATE SCHEMA p1_denorm;

-- ============================================================
-- 1. PENGGUNA + ALAMAT[]
-- One PostgreSQL row per user, addresses stored as JSONB array.
-- ============================================================
CREATE TABLE p1_denorm.pengguna AS
SELECT
    u.id_pengguna,
    u.nama,
    u.email,
    u.no_telp,
    u.password_hash,
    u.tanggal_daftar,
    COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'id_alamat',         a.id_alamat,
                'label_alamat',      a.label_alamat,
                'nama_penerima',     a.nama_penerima,
                'no_telp_penerima',  a.no_telp_penerima,
                'kota',              a.kota,
                'provinsi',          a.provinsi,
                'kode_pos',          a.kode_pos,
                'jalan',             a.jalan
            )
            ORDER BY a.id_alamat
        ) FILTER (WHERE a.id_alamat IS NOT NULL),
        '[]'::jsonb
    ) AS alamat
FROM pengguna u
LEFT JOIN alamat a
    ON a.id_pengguna = u.id_pengguna
GROUP BY
    u.id_pengguna,
    u.nama,
    u.email,
    u.no_telp,
    u.password_hash,
    u.tanggal_daftar;

ALTER TABLE p1_denorm.pengguna
    ADD PRIMARY KEY (id_pengguna);


-- ============================================================
-- 2. PRODUK + KATEGORI{}
-- Project-0 seed creates one category row for each product.
-- status_produk is retained for the SQL baseline.
-- CouchDB migration may omit it because status is stored in Valkey.
-- ============================================================
CREATE TABLE p1_denorm.produk AS
SELECT
    p.id_produk,
    p.id_pengguna AS id_penjual,
    p.nama_produk,
    p.deskripsi,
    p.ukuran,
    p.kondisi,
    p.harga_jual,
    p.harga_sewa,
    p.status_produk,
    p.tanggal_dibuat,
    (
        SELECT jsonb_build_object(
            'id_kategori',   k.id_kategori,
            'nama_kategori', k.nama_kategori
        )
        FROM kategori k
        WHERE k.id_produk = p.id_produk
        ORDER BY k.id_kategori
        LIMIT 1
    ) AS kategori
FROM produk p;

ALTER TABLE p1_denorm.produk
    ADD PRIMARY KEY (id_produk);


-- ============================================================
-- 3. ULASAN
-- Kept as its own aggregate/document, matching the logical model.
-- ============================================================
CREATE TABLE p1_denorm.ulasan AS
SELECT
    u.id_ulasan,
    u.id_produk,
    u.id_pengguna,
    u.rating,
    u.komentar,
    u.tanggal_ulasan
FROM ulasan u;

ALTER TABLE p1_denorm.ulasan
    ADD PRIMARY KEY (id_ulasan);


-- ============================================================
-- 4. PESANAN AGGREGATE
--
-- One PostgreSQL row per order.
-- Embedded structures:
--   pembayaran      : JSONB object (logical 1:1)
--   pengiriman      : JSONB array  (supports resend / multiple shipments)
--   detail_pesanan  : JSONB array
--       penyewaan   : optional embedded object
--           pengembalian : optional embedded object
--
-- Statuses remain inside this SQL baseline so PostgreSQL can answer
-- business queries independently. During CouchDB migration, status fields
-- can be removed because they are seeded separately to Valkey.
-- ============================================================
CREATE TABLE p1_denorm.pesanan AS
SELECT
    ps.id_pesanan,
    ps.id_penjual,
    ps.id_pembeli,
    ps.id_alamat,
    ps.tanggal_pesanan,
    ps.status_pesanan,

    COALESCE(
        (
            SELECT SUM(dp_total.harga)
            FROM detail_pesanan dp_total
            WHERE dp_total.id_pesanan = ps.id_pesanan
        ),
        0::numeric
    ) AS total_pesanan,

    (
        SELECT jsonb_build_object(
            'id_pembayaran',      pb.id_pembayaran,
            'metode_pembayaran',  pb.metode_pembayaran,
            'no_referensi',       pb.no_referensi,
            'nominal',            pb.nominal,
            'status_pembayaran',  pb.status_pembayaran::text,
            'waktu_pembayaran',   pb.waktu_pembayaran,
            'bukti_pembayaran',   pb.bukti_pembayaran
        )
        FROM pembayaran pb
        WHERE pb.id_pesanan = ps.id_pesanan
        ORDER BY pb.id_pembayaran DESC
        LIMIT 1
    ) AS pembayaran,

    COALESCE(
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'id_pengiriman',      pg.id_pengiriman,
                    'kurir',              pg.kurir,
                    'no_resi',            pg.no_resi,
                    'tanggal_kirim',       pg.tanggal_kirim,
                    'status_pengiriman',   pg.status_pengiriman::text,
                    'tanggal_terima',      pg.tanggal_terima
                )
                ORDER BY pg.id_pengiriman
            )
            FROM pengiriman pg
            WHERE pg.id_pesanan = ps.id_pesanan
        ),
        '[]'::jsonb
    ) AS pengiriman,

    COALESCE(
        (
            SELECT jsonb_agg(
                (
                    jsonb_build_object(
                        'id_detail',        dp.id_detail,
                        'no_urut',          dp.no_urut,
                        'id_produk',        dp.id_produk,
                        'jenis_transaksi',  dp.jenis_transaksi::text,
                        'harga',            dp.harga
                    )
                    ||
                    CASE
                        WHEN py.id_penyewaan IS NULL THEN '{}'::jsonb
                        ELSE jsonb_build_object(
                            'penyewaan',
                            (
                                jsonb_build_object(
                                    'id_penyewaan',          py.id_penyewaan,
                                    'tanggal_mulai_sewa',     py.tanggal_mulai_sewa,
                                    'tanggal_selesai_sewa',   py.tanggal_selesai_sewa,
                                    'durasi_hari',            py.durasi_hari,
                                    'deposit',                py.deposit,
                                    'status_sewa',            py.status_sewa::text
                                )
                                ||
                                CASE
                                    WHEN pgm.id_pengembalian IS NULL THEN '{}'::jsonb
                                    ELSE jsonb_build_object(
                                        'pengembalian',
                                        jsonb_build_object(
                                            'id_pengembalian',       pgm.id_pengembalian,
                                            'tanggal_pengembalian',  pgm.tanggal_pengembalian,
                                            'kondisi_sebelum',       pgm.kondisi_sebelum,
                                            'kondisi_sesudah',       pgm.kondisi_sesudah,
                                            'hasil_analisis_ai',     pgm.hasil_analisis_ai,
                                            'catatan_kerusakan',     pgm.catatan_kerusakan,
                                            'status_pengembalian',   pgm.status_pengembalian::text,
                                            'bukti_foto_video',      pgm.bukti_foto_video,
                                            'tanda_tangan_digital',  pgm.tanda_tangan_digital
                                        )
                                    )
                                END
                            )
                        )
                    END
                )
                ORDER BY dp.no_urut, dp.id_detail
            )
            FROM detail_pesanan dp
            LEFT JOIN penyewaan py
                ON py.id_detail = dp.id_detail
            LEFT JOIN pengembalian pgm
                ON pgm.id_penyewaan = py.id_penyewaan
            WHERE dp.id_pesanan = ps.id_pesanan
        ),
        '[]'::jsonb
    ) AS detail_pesanan

FROM pesanan ps;

ALTER TABLE p1_denorm.pesanan
    ADD PRIMARY KEY (id_pesanan);


-- ============================================================
-- 5. RUANG_CHAT + PESAN_CHAT[]
-- Status pesan is retained in PostgreSQL baseline.
-- During CouchDB migration it can be omitted and placed in Valkey.
-- ============================================================
CREATE TABLE p1_denorm.ruang_chat AS
SELECT
    rc.id_ruang_chat,
    rc.id_penjual,
    rc.id_pembeli,
    COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'id_pesan',     pc.id_pesan,
                'id_pengirim',  pc.id_pengguna,
                'pesan',        pc.pesan,
                'waktu_kirim',  pc.waktu_kirim,
                'status',       pc.status
            )
            ORDER BY pc.waktu_kirim, pc.id_pesan
        ) FILTER (WHERE pc.id_pesan IS NOT NULL),
        '[]'::jsonb
    ) AS pesan_chat
FROM ruang_chat rc
LEFT JOIN pesan_chat pc
    ON pc.id_ruang_chat = rc.id_ruang_chat
GROUP BY
    rc.id_ruang_chat,
    rc.id_penjual,
    rc.id_pembeli;

ALTER TABLE p1_denorm.ruang_chat
    ADD PRIMARY KEY (id_ruang_chat);


-- ============================================================
-- 6. FAVORIT PER USER
-- Mirrors the access pattern later represented as a Valkey SET.
-- PostgreSQL uses BIGINT[] for the denormalized baseline.
-- ============================================================
CREATE TABLE p1_denorm.produk_favorit_user AS
SELECT
    u.id_pengguna,
    COALESCE(
        array_agg(pf.id_produk ORDER BY pf.id_produk)
            FILTER (WHERE pf.id_produk IS NOT NULL),
        ARRAY[]::bigint[]
    ) AS id_produk
FROM pengguna u
LEFT JOIN produk_favorit pf
    ON pf.id_pengguna = u.id_pengguna
GROUP BY u.id_pengguna;

ALTER TABLE p1_denorm.produk_favorit_user
    ADD PRIMARY KEY (id_pengguna);


-- ============================================================
-- 7. ROOM MEMBERSHIP PER USER
-- Mirrors ruang_chat:{id_pengguna} -> SET<id_ruang_chat> in Valkey.
-- ============================================================
CREATE TABLE p1_denorm.ruang_chat_user AS
WITH membership AS (
    SELECT id_penjual AS id_pengguna, id_ruang_chat
    FROM ruang_chat

    UNION ALL

    SELECT id_pembeli AS id_pengguna, id_ruang_chat
    FROM ruang_chat
)
SELECT
    u.id_pengguna,
    COALESCE(
        array_agg(DISTINCT m.id_ruang_chat ORDER BY m.id_ruang_chat)
            FILTER (WHERE m.id_ruang_chat IS NOT NULL),
        ARRAY[]::bigint[]
    ) AS id_ruang_chat
FROM pengguna u
LEFT JOIN membership m
    ON m.id_pengguna = u.id_pengguna
GROUP BY u.id_pengguna;

ALTER TABLE p1_denorm.ruang_chat_user
    ADD PRIMARY KEY (id_pengguna);


-- ============================================================
-- 8. EXPORT VIEWS FOR VALKEY SEEDING
-- These are migration helpers only, not Valkey indexes.
-- ============================================================

CREATE VIEW p1_denorm.valkey_status_export AS
SELECT
    'status:produk:' || id_produk::text AS key,
    status_produk::text AS value
FROM produk

UNION ALL

SELECT
    'status:pesanan:' || id_pesanan::text,
    status_pesanan::text
FROM pesanan

UNION ALL

SELECT
    'status:pembayaran:' || id_pembayaran::text,
    status_pembayaran::text
FROM pembayaran

UNION ALL

SELECT
    'status:pengiriman:' || id_pengiriman::text,
    status_pengiriman::text
FROM pengiriman

UNION ALL

SELECT
    'status:penyewaan:' || id_penyewaan::text,
    status_sewa::text
FROM penyewaan

UNION ALL

SELECT
    'status:pengembalian:' || id_pengembalian::text,
    status_pengembalian::text
FROM pengembalian

UNION ALL

SELECT
    'status:pesan_chat:' || id_pesan::text,
    status::text
FROM pesan_chat;


CREATE VIEW p1_denorm.valkey_favorit_export AS
SELECT
    id_pengguna,
    id_produk
FROM produk_favorit;


CREATE VIEW p1_denorm.valkey_ruang_chat_export AS
SELECT id_penjual AS id_pengguna, id_ruang_chat
FROM ruang_chat

UNION

SELECT id_pembeli AS id_pengguna, id_ruang_chat
FROM ruang_chat;


COMMIT;


-- ============================================================
-- VERIFICATION QUERIES (run manually after the script succeeds)
-- ============================================================

-- Expected source/denorm root counts should match:
-- SELECT
--     (SELECT COUNT(*) FROM pengguna)           AS src_pengguna,
--     (SELECT COUNT(*) FROM p1_denorm.pengguna) AS denorm_pengguna;
--
-- SELECT
--     (SELECT COUNT(*) FROM produk)           AS src_produk,
--     (SELECT COUNT(*) FROM p1_denorm.produk) AS denorm_produk;
--
-- SELECT
--     (SELECT COUNT(*) FROM pesanan)           AS src_pesanan,
--     (SELECT COUNT(*) FROM p1_denorm.pesanan) AS denorm_pesanan;
--
-- SELECT
--     (SELECT COUNT(*) FROM ulasan)           AS src_ulasan,
--     (SELECT COUNT(*) FROM p1_denorm.ulasan) AS denorm_ulasan;
--
-- SELECT
--     (SELECT COUNT(*) FROM ruang_chat)           AS src_ruang_chat,
--     (SELECT COUNT(*) FROM p1_denorm.ruang_chat) AS denorm_ruang_chat;
--
-- Inspect sample aggregates:
-- SELECT * FROM p1_denorm.pengguna ORDER BY id_pengguna LIMIT 3;
-- SELECT * FROM p1_denorm.produk ORDER BY id_produk LIMIT 3;
-- SELECT * FROM p1_denorm.pesanan ORDER BY id_pesanan LIMIT 3;
-- SELECT * FROM p1_denorm.ruang_chat ORDER BY id_ruang_chat LIMIT 3;
--
-- Inspect migration helper views:
-- SELECT * FROM p1_denorm.valkey_status_export LIMIT 20;
-- SELECT * FROM p1_denorm.valkey_favorit_export LIMIT 20;
-- SELECT * FROM p1_denorm.valkey_ruang_chat_export LIMIT 20;
