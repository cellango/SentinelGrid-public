"""Read-only inventory of the files a developer could commit for review."""

from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_INVENTORY = Path("publication/source-files.json")


def source_files(root: Path = ROOT) -> list[Path]:
    """Include tracked changes and non-ignored new files, excluding deletions.

    Gitignore never exempts an already tracked file from this inventory.
    Symlinks are retained so callers can reject them without following targets.
    """
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others",
         "--exclude-standard", "-z"],
        check=True, capture_output=True,
    )
    names = sorted(set(result.stdout.decode("utf-8").split("\0")) - {""})
    return [root / name for name in names
            if (root / name).is_file() or (root / name).is_symlink()]


def publication_inventory_failures(files: list[Path], root: Path = ROOT) -> list[str]:
    """Detect path-selection drift without treating the inventory as a scan filter."""
    try:
        inventory = json.loads((root / PUBLICATION_INVENTORY).read_text())
    except (OSError, ValueError):
        return [f"Missing or invalid publication inventory: {PUBLICATION_INVENTORY}"]
    names = inventory.get("files") if isinstance(inventory, dict) else None
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        return ["Publication inventory must contain a list of file paths"]
    failures = []
    if names != sorted(set(names)):
        failures.append("Publication inventory must be sorted with no duplicate paths")
    current = {p.relative_to(root).as_posix() for p in files}
    selected = set(names)
    if current - selected:
        failures.append(f"Publication inventory omits {len(current - selected)} candidate paths")
    if selected - current:
        failures.append(f"Publication inventory has {len(selected - current)} absent paths")
    return failures


def private_file_reason(relative: Path) -> str | None:
    parts = set(relative.parts)
    if parts & {".git", ".aws", ".ssh", ".claude", ".claire", ".clone",
                "node_modules", "__pycache__", "backups", "artifacts"}:
        return "local state, dependencies, or private artifacts"
    name = relative.name.lower()
    if (name == ".env" or name.startswith(".env.") or name.endswith(".env")):
        if not name.endswith((".example", ".sample", ".template")):
            return "environment configuration (use a synthetic example)"
    if (name in {"tfplan", "tfstate"} or ".tfstate." in name
            or name.endswith((".pem", ".key", ".p12", ".pfx", ".jks", ".db", ".sqlite",
                              ".sqlite3", ".dump", ".tfstate", ".tfvars", ".tfplan", ".srl", ".log"))):
        return "credential, local database, state, or log file"
    if relative.parts[:3] == ("docs", "assets", "html"):
        return "saved browser output without publication clearance"
    if name.endswith((".pkg", ".rpm", ".deb", ".exe", ".msi")):
        return "installer binary without preview redistribution clearance"
    if ("gitleaks-report" in name or name == "token_tmp.json"
            or "credentials" in name and name.endswith((".json", ".txt"))):
        return "potentially credential-bearing report or export"
    return None
