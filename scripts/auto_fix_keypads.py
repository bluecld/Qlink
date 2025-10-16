import re
import csv
from pathlib import Path

in_csv = Path(__file__).resolve().parents[1] / "Info" / "keypads_parsed.csv"
out_csv = Path(__file__).resolve().parents[1] / "Info" / "keypads_parsed_fixed.csv"

if not in_csv.exists():
    print("Input CSV not found:", in_csv)
    raise SystemExit(2)

rows = []
with in_csv.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

fixed = []
ambiguous = []
removed = 0

for r in rows:
    raw = (r.get("raw") or "").strip()
    # Skip obvious page/header/footer lines
    if not raw:
        removed += 1
        continue
    if "Page" in raw and "Station List" in raw:
        removed += 1
        continue
    if "file://" in raw:
        removed += 1
        continue

    station = (r.get("station") or "").strip()
    vantage = (r.get("vantage") or "").strip()
    name = (r.get("name") or "").strip()
    floor = (r.get("floor") or "").strip()
    gang = (r.get("gang") or "").strip()
    buttons = (r.get("buttons") or "").strip()
    serial = (r.get("serial") or "").strip()

    # If vantage glued to station, e.g. '2-1V72' or '1-33V73', extract
    if not vantage:
        m = re.search(r"(?:^|\s)(?P<station>\d+-\d+|\d+)?(?P<v>V\d{1,3})", raw)
        if m:
            if not station and m.group("station"):
                station = m.group("station")
            if not vantage:
                vantage = m.group("v")

    # If vantage present but glued to following name (e.g. 'V14W-Hall'), separate
    if vantage and not name:
        # split raw at vantage
        parts = raw.split(vantage, 1)
        if len(parts) > 1:
            after = parts[1]
            # remove trailing tokens like floor/gang/serial
            after = re.sub(r"\d{5,8}.*$", "", after).strip(" ,-")
            # remove common 'new 03- 13' artifacts
            after = re.sub(r"new\s*03-?\s*13", "", after, flags=re.I).strip()
            name = re.sub(r"\s+", " ", after)

    # If name contains vantage (parser placed it there), remove the vantage portion
    if vantage and name.startswith(vantage):
        name = name[len(vantage) :].strip(" ,-")

    # Clean typical OCR artifacts
    name = re.sub(r"\s{2,}", " ", name)
    name = re.sub(r"\s+Rm", " Rm", name)

    # If serial missing, look for 5-8 digit at end of raw
    if not serial:
        sers = re.findall(r"\b(\d{5,8})\b", raw)
        if sers:
            serial = sers[-1]

    # If buttons missing and serial exists, find number preceding serial
    if not buttons and serial:
        m = re.search(r"(\d{1,2})\s+" + re.escape(serial), raw)
        if m:
            buttons = m.group(1)

    # Remove 'V##' duplicates in name
    if name and re.search(r"V\d{1,3}", name):
        name = re.sub(r"V\d{1,3}", "", name).strip(" ,-")

    # Final cleanup for name: remove leftover leading punctuation/nums
    name = re.sub(r"^[\-\s0-9:]+", "", name)
    name = name.strip()

    # Standardize floor text
    if floor:
        floor = floor.replace("1st Floor", "1st Floor").replace(
            "2nd Floor", "2nd Floor"
        )

    newr = {
        "station": station,
        "vantage": vantage,
        "name": name,
        "floor": floor,
        "gang": gang,
        "buttons": buttons,
        "serial": serial,
        "type": "Keypad",
        "raw": raw,
    }

    if not (newr["vantage"] and newr["serial"] and newr["name"]):
        ambiguous.append(newr)

    fixed.append(newr)

# Write fixed CSV
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
    for r in fixed:
        writer.writerow(r)

print(f"Processed {len(rows)} rows, removed {removed} header/footer rows")
print(f"Fixed {len(fixed)} rows, ambiguous after fix: {len(ambiguous)}")
if ambiguous:
    print("\nSample ambiguous rows:")
    for a in ambiguous[:12]:
        print("-", a["raw"][:200])
    print("\nYou can manually inspect", out_csv)
else:
    print("\nAll rows now look structured. Wrote", out_csv)
