from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from collections import defaultdict
from utils.read import ReadClient, clean_id, money, output_id, paid_orders, run_report


def get_top_penjual_pendapatan(client=None):
    client = client or ReadClient()
    totals = defaultdict(lambda: money(0))
    sold = defaultdict(set)
    for order, payment_count in paid_orders(client):
        if order.get("status_pesanan") != "selesai":
            continue
        for detail in order.get("detail_pesanan") or []:
            if detail.get("jenis_transaksi") != "beli":
                continue
            seller_id = clean_id(order["id_penjual"])
            totals[seller_id] += money(detail.get("harga")) * payment_count
            sold[seller_id].add(clean_id(detail["id_produk"]))
    users = client.documents("pengguna", totals)
    result = [
        {
            "id_pengguna": output_id(seller_id),
            "nama_penjual": users[seller_id].get("nama"),
            "total_pendapatan": total,
            "jumlah_produk_terjual": len(sold[seller_id]),
        }
        for seller_id, total in totals.items() if seller_id in users
    ]
    result.sort(key=lambda row: row["total_pendapatan"], reverse=True)
    return result[:20]


if __name__ == "__main__":
    run_report(4, "TOP PENJUAL PENDAPATAN", get_top_penjual_pendapatan)
