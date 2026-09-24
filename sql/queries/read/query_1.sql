--Tren pendapatan bulanan per kategori produk
SELECT 
    TO_CHAR(ps.tanggal_pesanan, 'YYYY-MM') AS bulan,
    k.nama_kategori,
    SUM(dp.harga) AS total_pendapatan
FROM pesanan ps
JOIN detail_pesanan dp ON ps.id_pesanan = dp.id_pesanan
JOIN produk pr ON dp.id_produk = pr.id_produk
JOIN kategori k ON pr.id_produk = k.id_produk
GROUP BY TO_CHAR(ps.tanggal_pesanan, 'YYYY-MM'), k.nama_kategori
ORDER BY bulan DESC, total_pendapatan DESC;