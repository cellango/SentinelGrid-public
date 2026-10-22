import json
from pathlib import Path
from app.authority.contracts import canonical, digest


def test_fixed_canonical_and_hash_vectors():
    data = json.loads(Path(__file__).with_name("canonical-vectors.json").read_text())
    for vector in data["vectors"]:
        assert canonical(vector["input"]) == vector["canonical_utf8"].encode("utf-8")
        assert digest(vector["input"]) == vector["sha256"]
