#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/smartshot" ]]; then
  echo "SmartShot is not installed yet."
  exit 1
fi

.venv/bin/smartshot uninstall
