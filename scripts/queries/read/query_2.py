from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from collections import defaultdict
from utils.read import ReadClient, clean_id, money, output_id, paid_orders, run_report


def get_top_pengguna_belanja(client=None):
    client = client or ReadClient()
    totals = defaultdict(lambda: money(0))
    for order, payment_count in paid_orders(client):
        for detail in order.get("detail_pesanan") or []:
            totals[clean_id(order["id_pembeli"])] += money(detail.get("harga")) * payment_count
    reviews = {
        clean_id(row["key"]): row["value"]
        for row in client.view("ulasan_per_pengguna", group=True)
    }
    users = client.documents("pengguna", totals)
    result = [
        {
            "id_pengguna": output_id(user_id),
            "nama_pengguna": users[user_id].get("nama"),
            "email": users[user_id].get("email"),
            "total_belanja": total,
            "jumlah_ulasan": reviews.get(user_id, 0),
        }
        for user_id, total in totals.items() if user_id in users
    ]
    result.sort(key=lambda row: row["total_belanja"], reverse=True)
    return result[:10]


if __name__ == "__main__":
    run_report(2, "TOP PENGGUNA TOTAL BELANJA", get_top_pengguna_belanja)
