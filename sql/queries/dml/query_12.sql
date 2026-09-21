-- Update status produk menjadi tersedia kembali setelah proses pengembalian penyewaan selesai.

UPDATE produk p
SET status_produk = 'tersedia'
FROM detail_pesanan dp
JOIN penyewaan py
    ON py.id_detail = dp.id_detail
JOIN pengembalian pg
    ON pg.id_penyewaan = py.id_penyewaan
WHERE p.id_produk = dp.id_produk
    AND p.id_produk = 1756
    AND pg.status_pengembalian = 'selesai';
