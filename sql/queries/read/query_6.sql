-- Daftar penyewaan yang memiliki status terlambat beserta dengan informasi pengguna, produk, dan status pengembalian
SELECT
    py.id_penyewaan,
    p.nama AS nama_pengguna,
    pr.nama_produk,
    py.tanggal_mulai_sewa,
    py.tanggal_selesai_sewa,
    py.status_sewa,
    pg.status_pengembalian
FROM penyewaan py
JOIN detail_pesanan dp
    ON py.id_detail = dp.id_detail
JOIN pesanan ps
    ON dp.id_pesanan = ps.id_pesanan
JOIN pengguna p
    ON ps.id_pembeli = p.id_pengguna
JOIN produk pr
    ON dp.id_produk = pr.id_produk
LEFT JOIN pengembalian pg
    ON py.id_penyewaan = pg.id_penyewaan
WHERE py.status_sewa = 'terlambat'
ORDER BY py.tanggal_selesai_sewa;