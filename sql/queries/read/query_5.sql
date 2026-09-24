-- Produk dengan jumlah penyewaan tertinggi beserta informasi jumlah ulasan dan rata-rata rating per produk
WITH jumlah_sewa_produk AS (
    SELECT
        dp.id_produk,
        COUNT(*) AS jumlah_penyewaan
    FROM detail_pesanan dp
    JOIN penyewaan py
        ON dp.id_detail = py.id_detail
    GROUP BY dp.id_produk
),
rating_produk AS (
    SELECT
        id_produk,
        COUNT(*) AS jumlah_ulasan,
        AVG(rating) AS rata_rata_rating
    FROM ulasan
    GROUP BY id_produk
)
SELECT
    p.id_produk,
    p.nama_produk,
    jsp.jumlah_penyewaan,
    COALESCE(rp.jumlah_ulasan, 0) AS jumlah_ulasan,
    COALESCE(ROUND(rp.rata_rata_rating, 2), 0) AS rata_rata_rating
FROM jumlah_sewa_produk jsp
JOIN produk p
    ON p.id_produk = jsp.id_produk
LEFT JOIN rating_produk rp
    ON p.id_produk = rp.id_produk
WHERE jsp.jumlah_penyewaan = (
    SELECT MAX(jumlah_penyewaan)
    FROM jumlah_sewa_produk
);