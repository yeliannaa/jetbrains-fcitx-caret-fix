#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
exec "${CARET_PYTHON:-python3}" -B tools/package_release.py package
