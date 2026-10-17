"""Connector test paths; no global SDK, service, identity or DDL substitutions."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT.parents[1] / "libs"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
