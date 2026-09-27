-- Pengguna yang pernah menyewa produk yang sama lebih dari satu kali
SELECT 
    p.nama AS nama_pembeli,
    pr.nama_produk,
    COUNT(*) AS jumlah_transaksi
FROM pesanan ps
JOIN pengguna p ON ps.id_pembeli = p.id_pengguna
JOIN detail_pesanan dp ON ps.id_pesanan = dp.id_pesanan
JOIN produk pr ON dp.id_produk = pr.id_produk
WHERE dp.jenis_transaksi = 'sewa'
GROUP BY p.id_pengguna, p.nama, pr.id_produk, pr.nama_produk
HAVING COUNT(*) > 1
ORDER BY jumlah_transaksi DESC;