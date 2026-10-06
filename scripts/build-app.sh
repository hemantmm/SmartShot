#!/usr/bin/env bash
set -e

# Change to the directory of this script's parent (project root)
cd "$(dirname "$0")/.."

echo "Building SmartShot.app with py2app..."

# Activate virtual environment if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Clean previous builds
rm -rf mac_build/build mac_build/dist dist

# Run py2app in an isolated directory so it doesn't read pyproject.toml
cd mac_build
python setup.py py2app
cd ..

# Move the app bundle to the root dist folder
mkdir -p dist
mv mac_build/dist/SmartShot.app dist/

echo "Build complete! Output is in dist/SmartShot.app"
