#!/usr/bin/env python3
"""
Simple script to load knowledge base using Docker exec.
This avoids needing to install all Python dependencies locally.
"""

from pathlib import Path
import subprocess
import sys
import os

def run_in_container(command):
    """Run command in model_gateway container."""
    docker_cmd = [
        "docker-compose", "-f", "docker-compose.dev.yml",
        "run", "--rm",
        "-e", "MODEL_GATEWAY_DATABASE_URL=postgresql://sg:sg@postgres:5432/sg",
        "model_gateway",
        "python", "-c", command
    ]
    return subprocess.run(docker_cmd, cwd=Path(__file__).resolve().parents[1])

if __name__ == "__main__":
    print("This script would run the load script in the container.")
    print("For now, let's use a direct Python approach...")
    print("\nTry running:")
    print("cd backend/services/model_gateway")
    print("python3 scripts/load_knowledge_base.py --all --database-url postgresql://sg:sg@localhost:5432/sg")

