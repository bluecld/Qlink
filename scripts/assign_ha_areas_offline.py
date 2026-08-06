#!/usr/bin/env python3
"""Offline HA area assignment: map Vantage light entities to per-room areas.

Runs on the KVM host against the HAOS data partition mounted at /mnt/hadata
(HA must be shut down). Reads room/load data from the running bridge's /config,
creates one HA area per room (reusing existing areas by name), and sets each
light entity's area_id. Backs up both registry files first.
"""
import datetime
import json
import re
import shutil
import urllib.request
from collections import Counter

STORAGE = "/mnt/hadata/supervisor/homeassistant/.storage"
AREA_FILE = STORAGE + "/core.area_registry"
ENT_FILE = STORAGE + "/core.entity_registry"
CONFIG_URL = "http://localhost:8000/config"

NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    return re.sub(r"_+", "_", s).strip("_") or "area"


# 1) load -> (floor, room) from the bridge config
cfg = json.load(urllib.request.urlopen(CONFIG_URL, timeout=15))
pair_of_load = {}
for room in cfg.get("rooms", []):
    rname = (room.get("name") or "").strip()
    floor = (room.get("floor") or "").strip()
    for ld in room.get("loads", []):
        lid = ld.get("id")
        if lid is not None and rname:
            pair_of_load[str(int(lid))] = (floor, rname)
print("loads mapped to a room:", len(pair_of_load))

pairs = sorted(set(pair_of_load.values()))
namecount = Counter(rn for _, rn in pairs)


def area_name(floor, rname):
    # Disambiguate rooms that repeat across floors
    if namecount[rname] > 1 and floor:
        return f"{rname} ({floor})"
    return rname


# 2) area registry: reuse by name, else create
area = json.load(open(AREA_FILE))
areas = area["data"]["areas"]
name_to_id = {(a.get("name") or "").strip().lower(): a["id"] for a in areas}
existing_ids = {a["id"] for a in areas}


def ensure_area(display_name):
    key = display_name.strip().lower()
    if key in name_to_id:
        return name_to_id[key]
    aid = slugify(display_name)
    base, i = aid, 2
    while aid in existing_ids:
        aid = f"{base}_{i}"
        i += 1
    areas.append(
        {
            "aliases": [],
            "floor_id": None,
            "humidity_entity_id": None,
            "icon": None,
            "id": aid,
            "labels": [],
            "name": display_name,
            "picture": None,
            "temperature_entity_id": None,
            "created_at": NOW,
            "modified_at": NOW,
        }
    )
    name_to_id[key] = aid
    existing_ids.add(aid)
    return aid


pair_to_area = {}
created_before = len(areas)
for floor, rname in pairs:
    pair_to_area[(floor, rname)] = ensure_area(area_name(floor, rname))
print(f"areas: {created_before} existing -> {len(areas)} total")

# 3) tag light entities
ent = json.load(open(ENT_FILE))
assigned = skipped = 0
for e in ent["data"]["entities"]:
    uid = e.get("unique_id") or ""
    if uid.startswith("vantage_load_"):
        pair = pair_of_load.get(uid[len("vantage_load_"):])
        if pair:
            aid = pair_to_area[pair]
            if e.get("area_id") != aid:
                e["area_id"] = aid
                e["modified_at"] = NOW
                assigned += 1
        else:
            skipped += 1
print(f"light entities assigned: {assigned}  skipped(no room): {skipped}")

# 4) backup + write
shutil.copy(AREA_FILE, AREA_FILE + ".bak")
shutil.copy(ENT_FILE, ENT_FILE + ".bak")
json.dump(area, open(AREA_FILE, "w"), indent=2)
json.dump(ent, open(ENT_FILE, "w"), indent=2)
print("registries written; backups saved (.bak)")
