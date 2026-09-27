from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.read import ReadClient, clean_id, run_report


def get_pengguna_sewa_berulang(client=None):
    client = client or ReadClient()
    rows = [
        row for row in client.view("penyewaan_by_user_produk", group=True)
        if row["value"] > 1
    ]
    users = client.documents("pengguna", (row["key"][0] for row in rows))
    products = client.documents("produk", (row["key"][1] for row in rows))
    result = []
    for row in rows:
        user_id, product_id = map(clean_id, row["key"])
        if user_id in users and product_id in products:
            result.append({
                "nama_pembeli": users[user_id].get("nama"),
                "nama_produk": products[product_id].get("nama_produk"),
                "jumlah_transaksi": row["value"],
            })
    result.sort(key=lambda row: row["jumlah_transaksi"], reverse=True)
    return result


if __name__ == "__main__":
    run_report(3, "PENGGUNA SEWA PRODUK BERULANG", get_pengguna_sewa_berulang)
