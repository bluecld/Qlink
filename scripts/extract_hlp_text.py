from pathlib import Path
import re

hlp_path = Path(__file__).resolve().parents[1] / "Info" / "QLINK.HLP"
out_path = Path(__file__).resolve().parents[1] / "Info" / "QLINK_extracted.txt"

if not hlp_path.exists():
    print("HLP file not found at", hlp_path)
    raise SystemExit(2)

data = hlp_path.read_bytes()

# Find printable ASCII runs (including basic punctuation) of length >= 4
runs = re.findall(rb"[\x20-\x7E\t]{4,}", data)

with out_path.open("wb") as f:
    for r in runs:
        # Replace multiple spaces with single space for readability
        line = re.sub(rb"\s+", b" ", r).strip()
        f.write(line + b"\n")

print(f"Wrote {len(runs)} text runs to {out_path}")
