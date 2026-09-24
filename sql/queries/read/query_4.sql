-- Top 20 penjual dengan total pendapatan tertinggi beserta jumlah produk yang telah terjual
SELECT
    p.id_pengguna,
    p.nama AS nama_penjual,
    SUM(dp.harga) AS total_pendapatan,
    COUNT(DISTINCT dp.id_produk) AS jumlah_produk_terjual
FROM pengguna p
JOIN pesanan ps
    ON p.id_pengguna = ps.id_penjual
JOIN detail_pesanan dp
    ON ps.id_pesanan = dp.id_pesanan
JOIN pembayaran pb
    ON ps.id_pesanan = pb.id_pesanan
WHERE pb.status_pembayaran = 'berhasil'
  AND ps.status_pesanan = 'selesai'
  AND dp.jenis_transaksi = 'beli'
GROUP BY p.id_pengguna, p.nama
ORDER BY total_pendapatan DESC
LIMIT 20;