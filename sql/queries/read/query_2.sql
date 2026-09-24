-- Top 10 pengguna dengan total belanja tertinggi beserta dengan jumlah ulasan
WITH total_belanja_user AS (
    SELECT 
        ps.id_pembeli AS id_pengguna,
        SUM(dp.harga) AS total_belanja
    FROM pesanan ps
    JOIN detail_pesanan dp ON ps.id_pesanan = dp.id_pesanan
    JOIN pembayaran pb ON ps.id_pesanan = pb.id_pesanan
    WHERE pb.status_pembayaran = 'berhasil'
    GROUP BY ps.id_pembeli
),
total_ulasan_user AS (
    SELECT 
        id_pengguna,
        COUNT(id_ulasan) AS jumlah_ulasan
    FROM ulasan
    GROUP BY id_pengguna
)
SELECT 
    p.id_pengguna,
    p.nama AS nama_pengguna,
    p.email,
    COALESCE(tb.total_belanja, 0) AS total_belanja,
    COALESCE(tu.jumlah_ulasan, 0) AS jumlah_ulasan
FROM pengguna p
JOIN total_belanja_user tb ON p.id_pengguna = tb.id_pengguna
LEFT JOIN total_ulasan_user tu ON p.id_pengguna = tu.id_pengguna
ORDER BY total_belanja DESC
LIMIT 10;