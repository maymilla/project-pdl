from datetime import datetime
from pathlib import Path
import time


def cetak_dan_simpan(
    judul: str,
    data: list[dict],
    output_file: str | Path,
    exec_time_ms: float = None,
    meta_extra: list[str] = None,
):
    output_path = Path(output_file)

    meta_lines = []
    if exec_time_ms is not None:
        meta_lines.append(f"Waktu Eksekusi : {exec_time_ms:.2f} ms")
    meta_lines.append(f"Total Record   : {len(data)}")

    if meta_extra:
        if isinstance(meta_extra, list):
            meta_lines.extend(meta_extra)
        else:
            meta_lines.append(str(meta_extra))

    hasil_lines = []
    if not data:
        hasil_lines.append("Tidak ada data ditemukan / Hasil kosong.")
        divider_len = 75
    else:
        keys = list(data[0].keys())

        col_widths = {}
        for k in keys:
            header_len = len(str(k))
            max_val_len = max(
                (
                    len(str(row.get(k) if row.get(k) is not None else "-"))
                    for row in data
                ),
                default=0,
            )
            col_widths[k] = max(header_len, max_val_len)

        header_str = " | ".join(
            f"{str(k).upper():<{col_widths[k]}}" for k in keys
        )
        divider_str = "-+-".join("-" * col_widths[k] for k in keys)
        divider_len = len(header_str)

        hasil_lines.append(header_str)
        hasil_lines.append(divider_str)

        for row in data:
            row_str = " | ".join(
                f"{str(row.get(k) if row.get(k) is not None else '-'):<{col_widths[k]}}"
                for k in keys
            )
            hasil_lines.append(row_str)

    lines = [judul, f"Waktu Jalan    : {datetime.now().isoformat()}"]
    lines += meta_lines
    lines += ["", "=" * divider_len]
    lines += hasil_lines

    output = "\n".join(lines)

    print(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output + "\n", encoding="utf-8")
    print(f"\n>>> Hasil tersimpan di: {output_path}\n")

    return output