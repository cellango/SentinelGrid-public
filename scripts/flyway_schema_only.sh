#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'The legacy migration launcher is unavailable in the source preview.
It will not connect, run SQL, launch Docker, repair/baseline, or create Flyway history.
Use scripts/prepare_iam_flyway.py only to assemble the reviewed IAM SQL location.
Actual Flyway execution and shared-baseline/role/extension/history qualification
require a separately reviewed installation/adoption procedure. Existing histories
and unknown populated databases must not be adopted or fabricated automatically.
' >&2
exit 2
