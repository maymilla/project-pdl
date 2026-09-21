
SELECT
    pr.nama_produk,
    pe.nama AS nama_penjual,
    pf.jumlah_favorit
FROM pengguna pe
JOIN produk pr
    ON pr.id_pengguna = pe.id_pengguna
JOIN (
    SELECT
        id_produk,
        COUNT(*) AS jumlah_favorit
    FROM produk_favorit
    GROUP BY id_produk
) pf
    ON pr.id_produk = pf.id_produk
WHERE pf.jumlah_favorit = (
    SELECT MAX(jumlah_favorit)
    FROM (
        SELECT
            id_produk,
            COUNT(*) AS jumlah_favorit
        FROM produk_favorit
        GROUP BY id_produk
    ) x
);