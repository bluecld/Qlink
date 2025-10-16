import re
import csv
from pathlib import Path
from PyPDF2 import PdfReader

pdf_path = Path(__file__).resolve().parents[1] / "Info" / "list of keypads.pdf"
out_csv = Path(__file__).resolve().parents[1] / "Info" / "keypads_parsed.csv"

if not pdf_path.exists():
    print("PDF not found at", pdf_path)
    raise SystemExit(2)

reader = PdfReader(str(pdf_path))
text = []
for p in reader.pages:
    text.append(p.extract_text() or "")
full = "\n".join(text)

# Split by 'Keypad' token — each entry ends with that word in the PDF
chunks = re.split(r"Keypad", full)

rows = []
ambiguous = []

for chunk in chunks:
    s = chunk.strip()
    if not s:
        continue
    # Attempt to parse fields
    # Station: starts with something like '2-4' or '1-3'
    station_m = re.match(r"\s*([0-9]+-[0-9]+|[0-9]+)", s)
    station = station_m.group(1) if station_m else ""

    vantage_m = re.search(r"\b(V\d{1,3})\b", s)
    vantage = vantage_m.group(1) if vantage_m else ""

    # serial: 5-8 digit number; take last occurrence
    serials = re.findall(r"\b(\d{5,8})\b", s)
    serial = serials[-1] if serials else ""

    # buttons: number appearing before serial (if any)
    buttons = ""
    if serial:
        m = re.search(r"(\d{1,2})\s+" + re.escape(serial), s)
        if m:
            buttons = m.group(1)

    # gang: look for pattern like '1 of 1'
    gang_m = re.search(r"(\d+\s+of\s+\d+)", s)
    gang = gang_m.group(1) if gang_m else ""

    # floor: try to find '1st Floor' or '2nd Floor' or 'Equipment'
    floor_m = re.search(r"\b(1st Floor|2nd Floor|Equipment|1st|2nd)\b", s)
    floor = floor_m.group(1) if floor_m else ""

    # name/room: take text between vantage and floor/gang
    name = ""
    if vantage:
        after_v = s.split(vantage, 1)[1].strip()
        # stop at floor or gang or serial
        stop_idx = len(after_v)
        for token in [gang, floor, serial]:
            if token and token in after_v:
                idx = after_v.find(token)
                if idx != -1:
                    stop_idx = min(stop_idx, idx)
        name = after_v[:stop_idx].strip(" ,-")
    else:
        # fallback: start after station
        if station:
            after_s = s[len(station) :].strip()
            name = after_s

    # Clean whitespace and reduce multiple spaces
    name = re.sub(r"\s+", " ", name)

    row = {
        "station": station,
        "vantage": vantage,
        "name": name,
        "floor": floor,
        "gang": gang,
        "buttons": buttons,
        "serial": serial,
        "type": "Keypad",
        "raw": s.replace("\n", " "),
    }

    # Heuristic to mark ambiguous rows
    if not (vantage and serial and name):
        ambiguous.append(row)
    rows.append(row)

# Write CSV
with out_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "station",
            "vantage",
            "name",
            "floor",
            "gang",
            "buttons",
            "serial",
            "type",
            "raw",
        ],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

print(f"Parsed {len(rows)} entries, {len(ambiguous)} ambiguous rows")
if ambiguous:
    print("\nSample ambiguous rows:")
    for a in ambiguous[:10]:
        print("-", a["raw"][:200])

print("\nWrote", out_csv)
