import json
import os
from typing import Dict, Set


def normalize_station_id(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return int(s)
        return None
    try:
        return int(value)
    except Exception:
        return None


def collect_stations(loads_path: str) -> Set[int]:
    stations: Set[int] = set()
    with open(loads_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "rooms" in data and isinstance(data["rooms"], list):
        for room in data["rooms"]:
            cand = normalize_station_id(room.get("station"))
            if cand is not None:
                stations.add(cand)
            for st in room.get("stations", []):
                cand2 = normalize_station_id(st.get("station"))
                if cand2 is not None:
                    stations.add(cand2)
    else:
        for key, val in data.items():
            if key.startswith("station_") and isinstance(val, dict):
                cand = normalize_station_id(val.get("station"))
                if cand is not None:
                    stations.add(cand)
    return stations


def merge_map(
    existing: Dict[int, int], stations: Set[int], default_fn
) -> Dict[int, int]:
    merged = dict(existing)
    added = 0
    for st in sorted(stations):
        if st not in merged:
            merged[st] = default_fn(st)
            added += 1
    return merged


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    loads_path = os.path.join(repo_root, "config", "loads.json")
    master_path = os.path.join(repo_root, "config", "station_master_map.json")
    phys_path = os.path.join(repo_root, "config", "station_physical_map.json")

    stations = collect_stations(loads_path)

    # Load existing maps
    master_map: Dict[int, int] = {}
    phys_map: Dict[int, int] = {}
    if os.path.exists(master_path):
        with open(master_path, "r", encoding="utf-8") as f:
            master_map = {int(k): int(v) for k, v in json.load(f).items()}
    if os.path.exists(phys_path):
        with open(phys_path, "r", encoding="utf-8") as f:
            phys_map = {int(k): int(v) for k, v in json.load(f).items()}

    merged_master = merge_map(master_map, stations, lambda st: 2 if st >= 51 else 1)
    merged_phys = merge_map(phys_map, stations, lambda st: st)

    # Write back sorted by key for readability
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in sorted(merged_master.items())}, f, indent=2)
        f.write("\n")
    with open(phys_path, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in sorted(merged_phys.items())}, f, indent=2)
        f.write("\n")

    print(f"Updated maps with {len(stations)} stations.")


if __name__ == "__main__":
    main()
