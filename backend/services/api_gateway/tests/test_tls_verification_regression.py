from pathlib import Path


def test_api_gateway_routes_do_not_hardcode_verify_false():
    api_dir = Path(__file__).resolve().parents[1] / "app" / "api"
    offenders: list[str] = []

    for path in sorted(api_dir.glob("routes_*.py")):
        content = path.read_text()
        if "verify=False" in content:
            offenders.append(path.name)

    assert offenders == [], f"verify=False must not appear in API gateway routes: {offenders}"
