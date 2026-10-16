"""
Seed the tool_registry table from the YAML seed file.

Intended usage:
    TOOL_REGISTRY_SEED=backend/config/tool_registry.seed.yaml python backend/scripts/seed_tool_registry.py

This is idempotent: existing tool IDs are skipped.
"""

import os
import sys
import yaml
from sqlalchemy import text
from sg_core.db import SessionLocal


def load_seed(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Seed file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("tools", [])


def upsert_tools(session, tools):
    inserted = 0
    for tool in tools:
        tool_id = tool.get("id")
        if not tool_id:
            continue
        exists = session.execute(
            text("SELECT 1 FROM tool_registry WHERE id = :id"),
            {"id": tool_id},
        ).first()
        if exists:
            continue
        session.execute(
            text(
                """
                INSERT INTO tool_registry
                    (id, name, category, job_types, image, command_template, parser_key, severity_map, tags, status, notes)
                VALUES
                    (:id, :name, :category, :job_types, :image, :command_template, :parser_key, :severity_map, :tags, :status, :notes)
                """
            ),
            {
                "id": tool_id,
                "name": tool.get("name"),
                "category": tool.get("category"),
                "job_types": tool.get("job_types") or [],
                "image": tool.get("image"),
                "command_template": tool.get("command_template") or {},
                "parser_key": tool.get("parser_key"),
                "severity_map": tool.get("severity_map") or {},
                "tags": tool.get("tags") or [],
                "status": tool.get("status", "active"),
                "notes": tool.get("notes"),
            },
        )
        inserted += 1
    session.commit()
    return inserted


def run_seed(seed_path: str = None) -> int:
    path = seed_path or os.getenv("TOOL_REGISTRY_SEED", "backend/config/tool_registry.seed.yaml")
    tools = load_seed(path)
    if not tools:
        return 0
    session = SessionLocal()
    try:
        inserted = upsert_tools(session, tools)
        return inserted
    finally:
        session.close()


def main():
    try:
        inserted = run_seed()
        print(f"Seed complete. Inserted {inserted} new tool(s).")
    except Exception as e:
        print(f"Failed to seed tool registry: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
