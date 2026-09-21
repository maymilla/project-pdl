-- Metode pembayaran yang paling sering digunakan beserta jumlah transaksi berhasil dan total nominal pembayarannya.

WITH statistik_pembayaran AS (
    SELECT
        metode_pembayaran,
        COUNT(*) AS jumlah_transaksi_berhasil,
        SUM(nominal) AS total_nominal
    FROM pembayaran
    WHERE status_pembayaran = 'berhasil'
    GROUP BY metode_pembayaran
)
SELECT
    metode_pembayaran,
    jumlah_transaksi_berhasil,
    total_nominal
FROM statistik_pembayaran
WHERE jumlah_transaksi_berhasil = (
    SELECT MAX(jumlah_transaksi_berhasil)
    FROM statistik_pembayaran
);

