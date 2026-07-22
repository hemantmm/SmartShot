#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON:-python3}"

echo "Installing SmartShot from: $ROOT_DIR"
echo "Using Python: $($PYTHON_BIN --version)"

"$PYTHON_BIN" -m venv .venv
. .venv/bin/activate

python -m pip install -U pip
python -m pip install -e ".[vision]"

chmod +x scripts/start-app.command scripts/install-background.command scripts/uninstall-background.command

echo
echo "SmartShot is installed."
echo
echo "Start the app:"
echo "  scripts/start-app.command"
echo
echo "Or run from Terminal:"
echo "  .venv/bin/smartshot app"
echo
echo "To make SmartShot work automatically after login:"
echo "  scripts/install-background.command"
echo
