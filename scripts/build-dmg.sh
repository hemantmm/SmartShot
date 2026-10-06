#!/usr/bin/env bash
set -e

# Change to project root
cd "$(dirname "$0")/.."

APP_PATH="dist/SmartShot.app"
DMG_PATH="dist/SmartShot-1.0.0.dmg"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found. Build the app first."
    exit 1
fi

echo "Creating DMG..."

# Create a temporary staging directory
STAGING_DIR=$(mktemp -d)
cp -r "$APP_PATH" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

# Remove old DMG if exists
rm -f "$DMG_PATH"

# Create the DMG
hdiutil create -volname "SmartShot" -srcfolder "$STAGING_DIR" -ov -format UDZO "$DMG_PATH"

# Clean up
rm -rf "$STAGING_DIR"

echo "DMG created at $DMG_PATH"
