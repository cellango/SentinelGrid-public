import sys
from pathlib import Path

# Ensure the service app package is importable for tests
ROOT = Path(__file__).resolve().parents[1]
LIBS = ROOT.parents[2] / "libs"
APP_ROOT = ROOT / "app"

for path in (ROOT, LIBS):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# The monorepo contains many top-level "app" packages. If another service's app
# module was imported first, clear it so ingestion resolves against this service.
existing_app = sys.modules.get("app")
existing_app_file = getattr(existing_app, "__file__", "") if existing_app else ""
existing_app_paths = [str(path) for path in getattr(existing_app, "__path__", [])] if existing_app else []
app_root = str(APP_ROOT)
app_points_to_service = (
    bool(existing_app_file and app_root in existing_app_file)
    or any(app_root == module_path or app_root in module_path for module_path in existing_app_paths)
)
if existing_app and not app_points_to_service:
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)
