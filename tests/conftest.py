import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

collect_ignore = [
    "archive/tools/stress_test.py",
    "tools/stress_test.py",
]
