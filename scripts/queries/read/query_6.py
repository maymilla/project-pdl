from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.read import ReadClient, clean_id, output_id, rental_details, run_report


def get_penyewaan_terlambat(client=None):
    client = client or ReadClient()
    rows = client.view("penyewaan_terlambat", include_docs=True)
    joined = list(rental_details(client, rows))
    users = client.documents("pengguna", (order.get("pembeli", {}).get("id_pengguna") for _, order, _ in joined))
    products = client.documents("produk", (detail["id_produk"] for _, _, detail in joined))
    result = []
    for row, order, detail in joined:
        user = users.get(clean_id(order.get("pembeli", {}).get("id_pengguna")))
        product = products.get(clean_id(detail["id_produk"]))
        if not user or not product:
            continue
        rental = row["doc"]
        returns = rental.get("pengembalian") or [{}]
        if isinstance(returns, dict):
            returns = [returns]
        for returned in returns:
            result.append({
                "id_penyewaan": output_id(rental.get("id_penyewaan", rental["_id"])),
                "nama_pengguna": user.get("nama"),
                "nama_produk": product.get("nama_produk"),
                "tanggal_mulai_sewa": rental.get("tanggal_mulai_sewa"),
                "tanggal_selesai_sewa": rental.get("tanggal_selesai_sewa"),
                "status_sewa": rental.get("status_sewa"),
                "status_pengembalian": returned.get("status_pengembalian"),
            })
    result.sort(key=lambda row: (
        row["tanggal_selesai_sewa"] is None, row["tanggal_selesai_sewa"] or ""
    ))
    return result


if __name__ == "__main__":
    run_report(6, "PENYEWAAN TERLAMBAT", get_penyewaan_terlambat)
