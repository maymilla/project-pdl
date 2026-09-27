-- Memperbarui status produk menjadi sedang disewa ketika transaksi penyewaan dimulai.

UPDATE produk p
SET status_produk = 'disewa'
FROM detail_pesanan dp
JOIN penyewaan py
    ON py.id_pesanan = dp.id_pesanan
    AND py.no_urut = dp.no_urut
WHERE p.id_produk = dp.id_produk
    AND py.status_sewa = 'berjalan'
    AND p.status_produk <> 'disewa';
