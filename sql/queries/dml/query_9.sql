-- Update status pesanan menjadi batal untuk pesanan yang melewati batas pembayaran.

UPDATE pesanan p
SET status_pesanan = 'dibatalkan'
WHERE p.status_pesanan = 'menunggu_pembayaran'
  AND p.tanggal_pesanan < CURRENT_TIMESTAMP - INTERVAL '24 hours'
  AND NOT EXISTS (
      SELECT 1
      FROM pembayaran pb
      WHERE pb.id_pesanan = p.id_pesanan
        AND pb.status_pembayaran = 'berhasil'
  );
