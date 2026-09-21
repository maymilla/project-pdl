-- Riwayat transaksi lengkap pengguna

SELECT
    u.nama,
    ps.id_pesanan,
    ps.tanggal_pesanan,
    p.nama_produk,
    dp.jenis_transaksi,
    dp.harga,
    ps.status_pesanan,
    pb.status_pembayaran,
    pk.status_pengiriman,
    py.status_sewa,
    pg.status_pengembalian
FROM pengguna u
JOIN pesanan ps
    ON u.id_pengguna = ps.id_pembeli
JOIN detail_pesanan dp
    ON ps.id_pesanan = dp.id_pesanan
JOIN produk p
    ON dp.id_produk = p.id_produk
LEFT JOIN pembayaran pb
    ON ps.id_pesanan = pb.id_pesanan
LEFT JOIN pengiriman pk
    ON ps.id_pesanan = pk.id_pesanan
LEFT JOIN penyewaan py
    ON dp.id_detail = py.id_detail
LEFT JOIN pengembalian pg
    ON py.id_penyewaan = pg.id_penyewaan
WHERE u.id_pengguna = 1
ORDER BY ps.tanggal_pesanan DESC;
