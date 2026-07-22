#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "SmartShot is not installed yet."
  echo "Run: scripts/install.sh"
  exit 1
fi

.venv/bin/python -m smartshot app
