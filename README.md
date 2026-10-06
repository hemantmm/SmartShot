# SmartShot

SmartShot is a macOS Menu Bar app and command-line tool that automatically organizes your screenshots using OCR-powered smart filenames.

macOS creates screenshots with names like:
- `Screenshot 2026-05-12 at 11.56.50.png`

SmartShot reads the screenshot text with Apple Vision OCR and renames the file to something searchable, like:
- `Login Error - 2026-05-12 at 11.56.50.png`

## How it works

1. You take a screenshot.
2. SmartShot detects it in the background.
3. Apple Vision OCR extracts text.
4. Smart naming heuristics generate a new filename.
5. The screenshot is automatically renamed.

## Features

- **Menu Bar Application**: Runs quietly in the background and shows you real-time activity and recently renamed files.
- **Background Monitoring**: Automatically monitors your Desktop (or any configured folder).
- **Smart Naming**: Prefers domains, filenames, and salient text from the image.
- **CLI for Power Users**: Manage screenshots via terminal.
- **Privacy-first**: All OCR and processing happens locally on your Mac.

## Download & Installation

*(Coming soon to GitHub Releases)*

For now, you can build SmartShot yourself from source:

### Building the macOS `.app`

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR-GITHUB-USERNAME/smartshot.git
   cd smartshot
   ```

2. Install dependencies:
   ```bash
   ./scripts/install.sh
   . .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. Build the application bundle:
   ```bash
   ./scripts/build-app.sh
   ```

4. The built app will be in `dist/SmartShot.app`. You can double-click it or drag it to your `Applications` folder.

## Development

Install the local app environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[vision,dev]"
```

Run the Menu Bar app locally during development:

```bash
smartshot-menubar
```

Or start the legacy Tkinter desktop app:

```bash
scripts/start-app.command
```

### Command Line Usage

Watch your Desktop and rename new screenshots automatically:

```bash
smartshot watch --dir ~/Desktop
```

Rename one file:

```bash
smartshot rename "~/Desktop/Screenshot 2026-05-30 at 12.34.56.png"
```

Rename existing screenshots in a folder:

```bash
smartshot backfill --dir ~/Desktop
```

Useful options:

- `--timestamp`: append the screenshot date/time to the filename.
- `--dry-run`: show what would happen without renaming files.
- `--force`: rename even when OCR is empty or unclear.
- `--all-images`: rename any new `.png`, `.jpg`, or `.jpeg`.

## Notes

- If OCR text contains a domain such as `superteam.fun`, SmartShot prefers the domain label, such as `superteam`.
- If OCR text contains a filename such as `naming.py`, SmartShot prefers the filename stem, such as `naming`.
- A manual LaunchAgent template is available at `launchd/com.smartshot.watch.plist`, but most users should use `smartshot install`.
