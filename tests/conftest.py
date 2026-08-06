import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

collect_ignore = [
    "archive/tools/stress_test.py",
    "tools/stress_test.py",
]


@pytest.fixture(autouse=True)
def _reset_enabler_circuit():
    """Reset the circuit breaker before each test so failure-path tests can't
    leave the enabler circuit 'open' and starve later tests' cache refreshes."""
    try:
        import app.bridge as b

        b._enabler_fail_streak = 0
        b._enabler_circuit_until = 0.0
    except Exception:
        pass
    yield
