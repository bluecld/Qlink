#!/usr/bin/env python3
"""Validate JSON config files in config/ against versioned JSON Schemas.

Usage:
  python scripts/validate_config.py [--strict]

Exits non-zero on validation failure.
"""

from __future__ import annotations

import json
import sys
import re
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except Exception:
    print(
        "jsonschema is required. Install with: pip install jsonschema", file=sys.stderr
    )
    raise


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
SCHEMA_DIR = CONFIG_DIR / "schemas"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validator_for(schema_name: str) -> Draft202012Validator:
    schema_path = SCHEMA_DIR / schema_name
    schema = load_json(schema_path)
    return Draft202012Validator(schema)


LOADS_ROOMS_V1 = validator_for("loads.rooms.v1.schema.json")
LOADS_LEGACY_V1 = validator_for("loads.legacy.stations.v1.schema.json")
TARGETS_V1 = validator_for("targets.v1.schema.json")


def validate_file(path: Path, strict: bool = False) -> list[str]:
    problems: list[str] = []
    try:
        data = load_json(path)
    except Exception as e:
        return [f"{path}: invalid JSON: {e}"]

    # Heuristics by filename/content
    if path.name.startswith("loads") and path.suffix == ".json":
        if isinstance(data, dict) and "rooms" in data:
            errors = sorted(LOADS_ROOMS_V1.iter_errors(data), key=lambda e: e.path)
            for err in errors:
                problems.append(f"{path}: {list(err.path)}: {err.message}")
        elif any(
            re.match(r"^station_\\d+$", k)
            for k in (data.keys() if isinstance(data, dict) else [])
        ):
            errors = sorted(LOADS_LEGACY_V1.iter_errors(data), key=lambda e: e.path)
            for err in errors:
                problems.append(f"{path}: {list(err.path)}: {err.message}")
        else:
            msg = f"{path}: could not determine schema (no 'rooms' and no 'station_*' keys)"
            if strict:
                problems.append(msg)
            else:
                print(f"[warn] {msg}")
    elif path.name == "targets.json" or path.name == "targets.example.json":
        errors = sorted(TARGETS_V1.iter_errors(data), key=lambda e: e.path)
        for err in errors:
            problems.append(f"{path}: {list(err.path)}: {err.message}")
    else:
        # Ignore other JSON files by default
        pass

    return problems


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    json_files = sorted(CONFIG_DIR.glob("*.json"))

    all_problems: list[str] = []
    for jf in json_files:
        all_problems.extend(validate_file(jf, strict=strict))

    if all_problems:
        print("Config validation failed:", file=sys.stderr)
        for p in all_problems:
            print(" - " + p, file=sys.stderr)
        return 1

    print("Config validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
