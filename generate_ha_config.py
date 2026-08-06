#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def fetch_bridge_config(url: str, secret: str | None = None) -> dict:
    request = urllib.request.Request(url)
    if secret:
        request.add_header("X-Bridge-Secret", secret.strip())
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def sanitize(name):
    s = (
        name.lower()
        .replace(" - ", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("&", "and")
        .replace('"', "")
    )
    s = "".join(c for c in s if c.isalnum() or c == "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")[:48]


def escape_yaml_string(s):
    """Escape string for YAML - replace quotes with inches symbol"""
    return s.replace('"', "'")


def build_url(base: str, path: str) -> str:
    base = (base or "").rstrip("/") or "http://localhost:8000"
    return f"{base}/{path.lstrip('/')}"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Home Assistant YAML for Vantage lights"
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Bridge /config URL (default: BRIDGE_CONFIG_URL or BRIDGE_BASE_URL + /config)",
    )
    parser.add_argument(
        "--bridge-base-url",
        default=None,
        help="Base URL for bridge endpoints used in generated YAML",
    )
    parser.add_argument(
        "--ha-in-docker",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("HA_IN_DOCKER", False),
        help="Use the Docker host bridge URL for HA (http://172.17.0.1:8000) when --bridge-base-url is not set.",
    )
    parser.add_argument(
        "--secret",
        default=os.getenv("BRIDGE_API_SECRET"),
        help="Bridge API secret (default: BRIDGE_API_SECRET env)",
    )
    parser.add_argument(
        "--scan-interval",
        type=int,
        default=int(os.getenv("HA_SCAN_INTERVAL", "60")),
        help="Polling interval (seconds) for REST sensors (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("HA_REQUEST_TIMEOUT", "10")),
        help="HTTP timeout (seconds) used for REST sensors (default: %(default)s)",
    )
    parser.add_argument(
        "--include-loads",
        default=os.getenv("HA_INCLUDE_LOADS", ""),
        help="Comma-separated list of load IDs to include in the generated config (default: all)",
    )
    parser.add_argument(
        "--use-aggregated",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("HA_USE_AGGREGATED", True),
        help="Generate a single aggregated REST sensor (GET /api/loads) and template sensors that read from it.",
    )
    parser.add_argument(
        "--use-subsets",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("HA_USE_SUBSETS", False),
        help="Generate 4 subset REST sensors (/api/loads/set1..set4) and template lights that read from them.",
    )
    parser.add_argument(
        "--use-priority",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("HA_USE_PRIORITY", True),
        help="Generate a priority REST sensor (/api/loads/priority) and prefer it in templates.",
    )
    parser.add_argument(
        "--priority-scan-interval",
        type=int,
        default=int(os.getenv("HA_PRIORITY_SCAN_INTERVAL", "30")),
        help="Polling interval (seconds) for priority REST sensor (default: %(default)s)",
    )
    # duplicate removed - the flag is already defined above
    args = parser.parse_args()

    secret = (args.secret or "").strip() or None
    config_url = (args.url or os.getenv("BRIDGE_CONFIG_URL") or "").strip()
    if not config_url:
        config_base = (os.getenv("BRIDGE_BASE_URL") or "").strip() or "http://localhost:8000"
        config_url = build_url(config_base, "/config")

    bridge_base_url = (args.bridge_base_url or "").strip()
    if not bridge_base_url:
        env_base = (os.getenv("BRIDGE_BASE_URL") or "").strip()
        if env_base:
            bridge_base_url = env_base
        elif args.ha_in_docker:
            bridge_base_url = "http://172.17.0.1:8000"
        else:
            bridge_base_url = "http://localhost:8000"

    try:
        config = fetch_bridge_config(config_url, secret)
    except urllib.error.HTTPError as err:
        print(
            f"Error fetching config from bridge ({err.code}): {err.reason}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Error fetching config from bridge: {exc}", file=sys.stderr)
        return 1

    loads = []
    raw_load_ids = []
    for room in config.get("rooms", []):
        for light in room.get("loads", []):
            lid = light.get("id")
            if lid is not None:
                raw_load_ids.append(int(lid))
            if light.get("type") in ["dimmer", "switch", "relay"]:
                loads.append(
                    {
                        "id": light["id"],
                        "floor": room.get("floor", ""),
                        "room": room.get("name", ""),
                        "name": light.get("name", ""),
                    }
                )

    loads.sort(key=lambda x: (x["floor"], x["room"], x["name"]))
    include_load_list = [
        int(x) for x in (args.include_loads or "").split(",") if x.strip().isdigit()
    ]
    if include_load_list:
        loads = [l for l in loads if l["id"] in include_load_list]

    print("# Vantage Q-Link - All Lights")
    print(f"# {len(loads)} lights\n")
    device_control_url = build_url(bridge_base_url, "device/{{ load_id }}/set")
    print("rest_command:")
    print("  vantage_light_on:")
    print(f'    url: "{device_control_url}"')
    print("    method: POST")
    print("    headers:")
    print('      Content-Type: "application/json"')
    print(
        '    payload: \'{"switch": "on", "brightness": {{ (brightness / 255 * 100) | round(0) }}}\''
    )
    print("")
    print("  vantage_light_off:")
    print(f'    url: "{device_control_url}"')
    print("    method: POST")
    print("    headers:")
    print('      Content-Type: "application/json"')
    print('    payload: \'{"switch": "off"}\'')
    use_subsets = bool(args.use_subsets)
    use_aggregated = bool(args.use_aggregated) and not use_subsets
    use_priority = bool(args.use_priority) and (use_subsets or use_aggregated)

    subset_map: dict[int, int] = {}
    if use_subsets:
        range_size = 34
        for idx, lid in enumerate(raw_load_ids):
            subset = idx // range_size + 1
            if subset > 4:
                subset = 4
            subset_map[int(lid)] = subset

    print("\nsensor:")
    if use_priority:
        print("  - platform: rest")
        print('    name: "Vantage Priority Loads"')
        print("    unique_id: vantage_priority_loads")
        print(f'    resource: "{build_url(bridge_base_url, "api/loads/priority")}"')
        print('    value_template: "{{ value_json.count | int }}"')
        print("    json_attributes:")
        print("      - loads")
        print(f"    scan_interval: {args.priority_scan_interval}")
        print(f"    timeout: {args.timeout}\n")

    if use_subsets:
        for subset in range(1, 5):
            print("  - platform: rest")
            print(f'    name: "Vantage Loads Set {subset}"')
            print(f"    unique_id: vantage_loads_set{subset}")
            print(
                f'    resource: "{build_url(bridge_base_url, f"api/loads/set{subset}")}"'
            )
            print('    value_template: "{{ value_json.count | int }}"')
            print("    json_attributes:")
            print("      - loads")
            print(f"    scan_interval: {args.scan_interval}")
            print(f"    timeout: {args.timeout}\n")
    elif use_aggregated:
        # Single aggregated REST sensor to fetch all loads (json_attributes)
        print("  - platform: rest")
        print('    name: "Vantage Loads"')
        print("    unique_id: vantage_loads")
        print(f'    resource: "{build_url(bridge_base_url, "api/loads")}"')
        print('    value_template: "{{ value_json.count | int }}"')
        # store loads map as attributes on this single sensor
        print("    json_attributes:")
        print("      - loads")
        print(f"    scan_interval: {args.scan_interval}")
        print(f"    timeout: {args.timeout}\n")
    else:
        for load in loads:
            print("  - platform: rest")
            print(f'    name: "Vantage Load {load["id"]} Status"')
            print(f"    unique_id: vantage_load_{load['id']}_status")
            status_path = f"load/{load['id']}/status"
            print(f'    resource: "{build_url(bridge_base_url, status_path)}"')
            print('    value_template: "{{ value_json.resp | int }}"')
            print(f"    scan_interval: {args.scan_interval}")
            print(f"    timeout: {args.timeout}\n")

    print("template:")
    print("  - light:")

    cf, cr = None, None
    for load in loads:
        if load["floor"] != cf:
            print(f"      # {load['floor']}")
            cf, cr = load["floor"], None
        if load["room"] != cr:
            print(f"      # {load['room']}")
            cr = load["room"]
        fn = escape_yaml_string(f"{load['room']} - {load['name']}")
        lid = load["id"]
        if use_subsets:
            subset = subset_map.get(lid, 4)
            fallback_expr = (
                f"(state_attr('sensor.vantage_loads_set_{subset}', 'loads') | "
                f"default({{}}, true)).get('{lid}', 0)"
            )
        elif use_aggregated:
            fallback_expr = (
                f"(state_attr('sensor.vantage_loads', 'loads') | "
                f"default({{}}, true)).get('{lid}', 0)"
            )
        else:
            fallback_expr = f"(states('sensor.vantage_load_{lid}_status') | int(0))"

        if use_priority:
            value_expr = (
                f"(state_attr('sensor.vantage_priority_loads', 'loads') | "
                f"default({{}}, true)).get('{lid}', {fallback_expr})"
            )
        else:
            value_expr = fallback_expr

        print(f'      - name: "{fn}"')
        print(f"        unique_id: vantage_load_{lid}")
        print(f'        state: "{{{{ (({value_expr}) | int) > 0 }}}}"')
        print(
            f'        level: "{{{{ ((({value_expr}) | int) * 2.55) | round(0) }}}}"'
        )
        print("        turn_on:")
        print("          action: rest_command.vantage_light_on")
        print("          data:")
        print(f"            load_id: {lid}")
        print('            brightness: "{{ brightness | default(255) }}"')
        print("        turn_off:")
        print("          action: rest_command.vantage_light_off")
        print("          data:")
        print(f"            load_id: {lid}")
        print("        set_level:")
        print("          action: rest_command.vantage_light_on")
        print("          data:")
        print(f"            load_id: {lid}")
        print('            brightness: "{{ brightness }}"')

    # HomeKit is managed via the HA UI integration (Settings > Devices & Services
    # > Add Integration > HomeKit Bridge), which reliably surfaces the pairing QR.
    # YAML-configured homekit hides the pairing code in a startup notification.

    print("\nrecorder:")
    print("  purge_keep_days: 3")
    print("  commit_interval: 30")
    print("  db_max_retries: 5")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
