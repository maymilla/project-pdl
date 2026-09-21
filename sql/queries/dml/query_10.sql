-- Memperbarui status penyewaan menjadi selesai setelah barang berhasil dikembalikan.

UPDATE penyewaan py
SET status_sewa = 'selesai'
FROM pengembalian pg
WHERE py.id_penyewaan = pg.id_penyewaan
  AND pg.id_pengembalian = 1
  AND pg.status_pengembalian = 'selesai';
