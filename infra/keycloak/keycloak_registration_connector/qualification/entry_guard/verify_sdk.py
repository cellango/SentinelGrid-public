#!/usr/bin/env python3
"""Check the resolved experimental classpath against reviewed SHA-256 inputs."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(classpath, repository, manifest):
    expected = {row["coordinate"]: row["sha256"] for row in manifest["artifacts"]}
    if len(expected) != len(manifest["artifacts"]):
        raise ValueError("Duplicate reviewed coordinate")
    actual = {}
    root = repository.resolve()
    for name in classpath.read_text().strip().split(":"):
        jar = Path(name).resolve()
        relative = jar.relative_to(root).parts
        if len(relative) < 4 or jar.suffix != ".jar":
            raise ValueError("Unexpected classpath entry")
        coordinate = ":".join([".".join(relative[:-3]), relative[-3], relative[-2]])
        if coordinate in actual:
            raise ValueError("Duplicate classpath coordinate")
        actual[coordinate] = hashlib.sha256(jar.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("Unreviewed SDK classpath or bytes")
    return {"verified_jars": len(actual), "production_qualification": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("classpath", type=Path)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    reviewed = json.loads((Path(__file__).resolve().parent / "sdk-inputs.json").read_text())
    print(json.dumps(verify(args.classpath, args.repository, reviewed), sort_keys=True))
