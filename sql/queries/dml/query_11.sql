-- Memperbarui status produk menjadi sedang disewa ketika transaksi penyewaan dimulai.

UPDATE produk p
SET status_produk = 'disewa'
FROM detail_pesanan dp
JOIN penyewaan py
    ON py.id_detail = dp.id_detail
WHERE p.id_produk = dp.id_produk
  AND py.id_penyewaan = 1
  AND py.status_sewa = 'berjalan';
