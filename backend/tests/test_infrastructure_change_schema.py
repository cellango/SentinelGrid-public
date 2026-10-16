"""Compare the pending cloud model with its independent Flyway DDL; no database."""

from pathlib import Path
import re
import sys

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/libs"))

from sg_core.models import InfrastructureChangeRequest

MIGRATION = (ROOT / "backend/migrations_consolidated/"
             "V013__public_hetzner_infrastructure_change_requests.sql").read_text()
TABLE = InfrastructureChangeRequest.__table__
BODY = MIGRATION.split("(\n", 1)[1].split("\n);", 1)[0]
DECLARATIONS = dict(line.strip().rstrip(",").split(None, 1)
                    for line in BODY.splitlines() if line.strip())


def _normalized(value):
    return re.sub(r"\s+", " ", str(value).strip()).lower()


def test_cloud_model_columns_match_flyway_types_and_nullability():
    assert set(TABLE.columns.keys()) == set(DECLARATIONS)
    for name, declaration in DECLARATIONS.items():
        sql_type = declaration.split()[0]
        if sql_type == "TIMESTAMPTZ":
            sql_type = "TIMESTAMP WITH TIME ZONE"
        column = TABLE.columns[name]
        assert column.type.compile(dialect=postgresql.dialect()) == sql_type, name
        assert column.primary_key == ("PRIMARY KEY" in declaration), name
        assert column.nullable == ("NOT NULL" not in declaration
                                   and "PRIMARY KEY" not in declaration), name


def test_cloud_model_server_defaults_match_flyway():
    for name, declaration in DECLARATIONS.items():
        default = re.search(r"\bDEFAULT\s+(.+)$", declaration)
        expected = _normalized(default.group(1)) if default else None
        actual = TABLE.columns[name].server_default
        assert (_normalized(actual.arg) if actual is not None else None) == expected, name


def test_cloud_model_schema_and_indexes_match_flyway():
    schema = re.search(r"SET search_path = (\w+);", MIGRATION).group(1)
    assert TABLE.schema == schema
    expected = {_normalized(statement).replace(" if not exists", "")
                for statement in re.findall(r"CREATE INDEX.*?;", MIGRATION, re.S)}
    actual = {_normalized(CreateIndex(index).compile(dialect=postgresql.dialect()))
              .replace(f"{schema}.", "") + ";" for index in TABLE.indexes}
    assert actual == expected
