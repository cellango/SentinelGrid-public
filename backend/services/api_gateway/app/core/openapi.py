"""Deterministic IDs for multi-method and slash-alias OpenAPI operations.

HTTP routes, dependencies, paths and existing unique operation IDs are unchanged.
Only ambiguous generated IDs are replaced; old duplicates cannot identify one
operation in a generated client. No endpoint or capability is enabled here.
"""

from collections import Counter
import hashlib
import re
import warnings

METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
)


def install_openapi(app):
    original = app.openapi

    def schema():
        if app.openapi_schema is not None:
            return app.openapi_schema
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Duplicate Operation ID .*",
                category=UserWarning,
                module="fastapi.openapi.utils",
            )
            value = original()
        operations = [
            (path, method, operation)
            for path, item in value["paths"].items()
            for method, operation in item.items()
            if method in METHODS
        ]
        counts = Counter(operation["operationId"] for _, _, operation in operations)
        used = {
            operation["operationId"]
            for _, _, operation in operations
            if counts[operation["operationId"]] == 1
        }
        for path, method, operation in operations:
            if counts[operation["operationId"]] == 1:
                continue
            wire = method.upper() + " " + path
            label = re.sub("[^a-zA-Z0-9_]+", "_", path).strip("_")[:80]
            candidate = (
                method
                + "_"
                + label
                + "_"
                + hashlib.sha256(wire.encode()).hexdigest()[:16]
            )
            if candidate in used:
                raise ValueError("Ambiguous OpenAPI operation identity")
            operation["operationId"] = candidate
            used.add(candidate)
        app.openapi_schema = value
        return value

    app.openapi = schema
