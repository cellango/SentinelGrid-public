from fastapi import FastAPI
from app.core.openapi import install_openapi
from app.main import app


def test_actual_gateway_schema_has_unique_ids_and_preserves_all_methods():
    schema = app.openapi()
    operations = [
        value
        for item in schema["paths"].values()
        for method, value in item.items()
        if method in {"get", "post", "put", "patch", "delete", "head", "options"}
    ]
    ids = [item["operationId"] for item in operations]
    assert len(ids) == len(set(ids))
    assert len(operations) >= 308
    assert app.openapi() is schema


def test_only_duplicate_ids_change_and_paths_methods_are_retained():
    local = FastAPI()

    @local.api_route("/alias/", methods=["GET", "POST"])
    @local.api_route("/alias", methods=["GET", "POST"])
    async def alias():
        return {}

    @local.get("/unique", operation_id="existing_unique_client_symbol")
    async def unique():
        return {}

    install_openapi(local)
    first = local.openapi()
    assert set(first["paths"]["/alias"]) == {"get", "post"}
    assert set(first["paths"]["/alias/"]) == {"get", "post"}
    assert (
        first["paths"]["/unique"]["get"]["operationId"]
        == "existing_unique_client_symbol"
    )
    ids = [v["operationId"] for item in first["paths"].values() for v in item.values()]
    assert len(ids) == len(set(ids)) == 5
    local.openapi_schema = None
    assert local.openapi() == first
