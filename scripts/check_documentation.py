"""Check Markdown paths against selected source, including moved documentation."""

from html import unescape
from pathlib import Path
import json
import os
import re
from urllib.parse import unquote, urlsplit

from public_preview import ROOT, source_files


def markdown_links(text: str) -> list[tuple[int, int, str]]:
    """Return URL spans, ignoring fenced and inline code examples."""
    masked = list(text)
    fence = None
    offset = 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r"\s{0,3}(?:>\s*)?(`{3,}|~{3,})", line)
        inside = fence is not None
        if marker:
            value = marker[1]
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
        if inside or marker:
            masked[offset:offset + len(line)] = ["\n" if c == "\n" else " " for c in line]
        offset += len(line)
    value = "".join(masked)
    for match in re.finditer(r"(`+)(?!`)(.+?)\1(?!`)", value):
        masked[match.start():match.end()] = " " * (match.end() - match.start())
    value = "".join(masked)
    result = []
    for match in re.finditer(r"!?\[[^\]\n]*\]\(", value):
        start = match.end()
        while start < len(value) and value[start].isspace():
            start += 1
        if start < len(value) and value[start] == "<":
            end = value.find(">", start + 1)
            if end >= 0:
                result.append((start + 1, end, text[start + 1:end]))
            continue
        end, depth = start, 0
        while end < len(value):
            char = value[end]
            if char == "\\":
                end += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            elif char.isspace() and depth == 0:
                break
            end += 1
        if end > start:
            result.append((start, end, text[start:end]))
    for match in re.finditer(r"(?m)^ {0,3}\[[^\]\n]+\]:\s*(?:<([^>]+)>|([^\s]+))", value):
        group = 1 if match[1] is not None else 2
        start, end = match.span(group)
        result.append((start, end, text[start:end]))
    return sorted(set(result))


def local_target(source: str, href: str, root: Path = ROOT) -> str | None:
    try:
        parsed = urlsplit(unescape(href))
    except ValueError:
        return "<invalid-link>"
    if parsed.scheme == "file":
        return "<outside-publication>"
    if parsed.scheme and parsed.scheme != "file" or parsed.netloc or not parsed.path:
        return None
    path = unquote(parsed.path)
    path = re.sub(r"\\([()\[\] ])", r"\1", path)
    target = root / path.lstrip("/") if path.startswith("/") else root / Path(source).parent / path
    try:
        return Path(os.path.abspath(target)).relative_to(Path(os.path.abspath(root))).as_posix()
    except ValueError:
        return "<outside-publication>"


def check_links(files: list[Path], root: Path = ROOT) -> list[str]:
    selected = {p.relative_to(root).as_posix() for p in files}
    failures = []
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        name = path.relative_to(root).as_posix()
        for _, _, href in markdown_links(path.read_text()):
            target = local_target(name, href, root)
            if (target is not None and target not in selected
                    and not (target == "." and selected)
                    and not any(n.startswith(target.rstrip("/") + "/") for n in selected)):
                failures.append(f"{name}: local documentation link has no selected publication target")
    return failures


def documentation_failures(files: list[Path], root: Path = ROOT) -> list[str]:
    failures = check_links(files, root)
    catalog = root / "publication/documentation.json"
    try:
        entries = json.loads(catalog.read_text())["files"]
        names = [entry["path"] for entry in entries]
        current = sorted(p.relative_to(root).as_posix() for p in files if p.suffix.lower() == ".md")
        if names != sorted(set(names)) or names != current:
            failures.append("Documentation classification differs from selected Markdown files")
        for entry in entries:
            expected = documentation_class(entry["path"])
            if expected == "unclassified_documentation_folder" or entry.get("class") != expected:
                failures.append("Documentation class does not match its maintained folder")
    except (OSError, ValueError, KeyError, TypeError):
        failures.append("Missing or invalid documentation classification")
    return failures


def documentation_class(name: str) -> str:
    if name == "AGENTS.md":
        return "contributor_instructions"
    if name == "docs/README.md":
        return "documentation_index"
    for directory, category in [("architecture", "current_architecture"),
                                ("development", "developer_guidance"),
                                ("reference", "current_source_reference"),
                                ("release", "publication_review"),
                                ("archive", "historical_reference")]:
        if name.startswith(f"docs/{directory}/"):
            return category
    if name.startswith("docs/"):
        return "unclassified_documentation_folder"
    if "/" not in name:
        return "repository_entrypoint"
    if name.startswith(("third_party/", ".github/")):
        return "repository_reference"
    return "experimental_component_reference"


if __name__ == "__main__":
    findings = documentation_failures(source_files())
    for finding in findings:
        print(f"FAIL: {finding}")
    print(f"Documentation checks: {len(findings)} failures.")
    raise SystemExit(bool(findings))
