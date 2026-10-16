#!/usr/bin/env bash

set -euo pipefail

curl http://localhost:8023/health
echo
curl http://localhost:8024/health
echo
