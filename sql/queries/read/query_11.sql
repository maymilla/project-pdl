-- Produk yang belum pernah mendapatkan ulasan.

SELECT
    p.id_produk,
    p.nama_produk,
    p.kondisi,
    p.harga_jual,
    p.harga_sewa,
    p.status_produk
FROM produk p
LEFT JOIN ulasan u
    ON p.id_produk = u.id_produk
WHERE u.id_ulasan IS NULL
ORDER BY p.id_produk
LIMIT 10;
