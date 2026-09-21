-- 10 produk yang memiliki rating di atas rata-rata keseluruhan produk, beserta jumlah ulasan dan nama kategorinya.

WITH rating_produk AS (
    SELECT
        id_produk,
        COUNT(*) AS jumlah_ulasan,
        AVG(rating) AS rata_rata_rating
    FROM ulasan
    GROUP BY id_produk
),
rating_keseluruhan AS (
    SELECT AVG(rating) AS rata_rata_keseluruhan
    FROM ulasan
)
SELECT
    p.id_produk,
    p.nama_produk,
    k.nama_kategori,
    rp.jumlah_ulasan,
    ROUND(rp.rata_rata_rating, 2) AS rata_rata_rating
FROM rating_produk rp
JOIN produk p
    ON p.id_produk = rp.id_produk
JOIN kategori k
    ON k.id_produk = p.id_produk
CROSS JOIN rating_keseluruhan rk
WHERE rp.rata_rata_rating > rk.rata_rata_keseluruhan
ORDER BY rp.rata_rata_rating DESC
LIMIT 10;
