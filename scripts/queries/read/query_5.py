from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from collections import Counter
from utils.read import ReadClient, clean_id, output_id, rating, rental_details, run_report


def get_produk_penyewaan_tertinggi(client=None):
    client = client or ReadClient()
    rows = client.view("penyewaan_per_detail", group=True)
    counts = Counter()
    for row, order, detail in rental_details(client, rows):
        counts[clean_id(detail["id_produk"])] += row["value"]
    if not counts:
        return []
    maximum = max(counts.values())
    top_ids = [product_id for product_id, count in counts.items() if count == maximum]
    products = client.documents("produk", top_ids)
    ratings = {
        clean_id(row["key"]): row["value"]
        for row in client.view("rating_per_produk", group=True)
    }
    return [
        {
            "id_produk": output_id(product_id),
            "nama_produk": products[product_id].get("nama_produk"),
            "jumlah_penyewaan": maximum,
            "jumlah_ulasan": ratings.get(product_id, {}).get("count", 0),
            "rata_rata_rating": rating(ratings.get(product_id, {})),
        }
        for product_id in top_ids if product_id in products
    ]


if __name__ == "__main__":
    run_report(5, "PRODUK PENYEWAAN TERTINGGI", get_produk_penyewaan_tertinggi)
