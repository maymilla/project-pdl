-- Produk yang paling sering dimasukkan ke daftar favorit beserta penjualnya.
-- Parameter :limit digunakan oleh runner Python (psycopg).

WITH jumlah_favorit AS (
    SELECT
        favorit.id_produk,
        COUNT(*) AS total_favorit
    FROM p1_denorm.produk_favorit_user
    CROSS JOIN LATERAL unnest(id_produk) AS favorit(id_produk)
    GROUP BY favorit.id_produk
)
SELECT
    produk.id_produk,
    produk.nama_produk,
    produk.id_penjual,
    penjual.nama AS nama_penjual,
    jumlah_favorit.total_favorit
FROM jumlah_favorit
JOIN p1_denorm.produk AS produk
    ON produk.id_produk = jumlah_favorit.id_produk
JOIN p1_denorm.pengguna AS penjual
    ON penjual.id_pengguna = produk.id_penjual
ORDER BY
    jumlah_favorit.total_favorit DESC,
    produk.id_produk ASC
LIMIT %(limit)s;