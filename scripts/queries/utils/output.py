from datetime import datetime
from pathlib import Path


def simpan_dan_print(judul, meta_lines, hasil_lines, output_file: Path):
  lines = [judul, f"Waktu jalan  : {datetime.now().isoformat()}"]
  lines += meta_lines
  lines += ["", "=" * 70]
  lines += hasil_lines
  output = "\n".join(lines)
  print(output)
  output_file.parent.mkdir(parents=True, exist_ok=True)
  output_file.write_text(output + "\n", encoding="utf-8")
  print(f"\n>>> Hasil lengkap tersimpan di: {output_file}")
  return output