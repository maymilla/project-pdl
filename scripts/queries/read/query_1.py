from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from collections import defaultdict
from utils.read import ReadClient, clean_id, money, run_report


def get_pendapatan_bulanan_per_kategori(client=None):
    client = client or ReadClient()
    rows = client.view("pendapatan_per_kategori", group=True)
    products = client.documents("produk", (row["key"][0] for row in rows))
    totals = defaultdict(lambda: money(0))
    for row in rows:
        product_id, month = row["key"]
        product = products.get(clean_id(product_id))
        if not product:
            continue
        categories = product.get("kategori") or []
        if isinstance(categories, dict):
            categories = [categories]
        for category in categories:
            totals[(month, category.get("nama_kategori"))] += money(row["value"])
    result = [
        {"bulan": month, "nama_kategori": category, "total_pendapatan": total}
        for (month, category), total in totals.items()
    ]
    result.sort(key=lambda row: (row["bulan"], row["total_pendapatan"]), reverse=True)
    return result


if __name__ == "__main__":
    run_report(1, "TREN PENDAPATAN BULANAN PER KATEGORI", get_pendapatan_bulanan_per_kategori)
