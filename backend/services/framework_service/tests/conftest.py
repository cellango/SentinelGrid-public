from pathlib import Path
import sys

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

