#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/smartshot" ]]; then
  echo "SmartShot is not installed yet."
  echo "Run: scripts/install.sh"
  exit 1
fi

.venv/bin/smartshot install --dir "$HOME/Desktop" --no-timestamp
.venv/bin/smartshot status

echo
echo "SmartShot will now run in the background after login."
echo "New screenshots saved to Desktop will be renamed automatically."
