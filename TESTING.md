Running tests & CI

This repository includes a GitHub Actions CI workflow that performs basic checks on push and pull requests:

- Lint: `ruff` (reports issues but currently does not fail the job)
- Type-check: `mypy` (runs with --ignore-missing-imports)
- Tests: `pytest` runs the test suite

Run tests locally:

```powershell
# Create a venv and install developer deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r dev-requirements.txt

# Run tests
pytest -q
```

If you don't have `dev-requirements.txt`, the CI will attempt an editable install using `pyproject.toml`.