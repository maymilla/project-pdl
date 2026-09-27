-- Update status produk menjadi tersedia kembali setelah proses pengembalian penyewaan selesai.

UPDATE produk p
SET status_produk = 'tersedia'
FROM detail_pesanan dp
JOIN penyewaan py
    ON py.id_pesanan = dp.id_pesanan 
    AND py.no_urut = dp.no_urut
JOIN pengembalian pg
    ON pg.id_penyewaan = py.id_penyewaan
WHERE p.id_produk = dp.id_produk
    AND pg.status_pengembalian = 'selesai'
    AND p.status_produk = 'disewa';
