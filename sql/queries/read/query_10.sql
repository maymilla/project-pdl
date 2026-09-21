-- Pengguna dengan jumlah transaksi pembelian dan penyewaan terbanyak.

SELECT
    u.id_pengguna,
    u.nama,
    COUNT(dp.id_detail) FILTER (
        WHERE dp.jenis_transaksi = 'beli'
    ) AS jumlah_pembelian,
    
    COUNT(dp.id_detail) FILTER (
        WHERE dp.jenis_transaksi = 'sewa'
    ) AS jumlah_penyewaan,
    
    COUNT(dp.id_detail) AS total_transaksi
FROM pengguna u
JOIN pesanan ps
    ON u.id_pengguna = ps.id_pembeli
JOIN detail_pesanan dp
    ON ps.id_pesanan = dp.id_pesanan
GROUP BY
    u.id_pengguna,
    u.nama
ORDER BY total_transaksi DESC
LIMIT 10;
