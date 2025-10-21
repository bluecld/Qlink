# Config Schemas

This project uses versioned JSON Schemas to validate configuration files.

## Schemas

- Loads (rooms/buttons v1): `config/schemas/loads.rooms.v1.schema.json`
- Loads (legacy station map v1): `config/schemas/loads.legacy.stations.v1.schema.json`
- Deployment targets v1: `config/schemas/targets.v1.schema.json`

## Validate Locally

```
pip install -r app/requirements.txt
python scripts/validate_config.py --strict
```

`--strict` fails when a JSON file in `config/` does not match a known schema.

## Runtime Validation

The bridge validates `config/loads.json` at runtime when it follows the rooms/buttons layout. Schema errors are logged as warnings.

## Editor Hints

Add a `$schema` property to JSON files for better IDE support:

```json
{
  "$schema": "config/schemas/loads.rooms.v1.schema.json",
  "rooms": []
}
```

