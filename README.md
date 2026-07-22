# SmartShot

SmartShot is a macOS app and command-line tool that renames screenshots based on
what is visible inside them.

macOS creates screenshots with names like:

- `Screenshot 2026-05-12 at 11.56.50.png`

SmartShot reads the screenshot text with OCR and renames the file to something
searchable, like:

- `Login Error - 2026-05-12 at 11.56.50.png`

It uses Apple Vision OCR on macOS when installed with the `vision` extra.

## Use Locally From GitHub

For now, SmartShot is meant to be used locally from a GitHub fork, clone, or
downloaded ZIP. Clone the repo, install the local environment, then start the
local app/watch process from the project folder. A Homebrew install path is
planned and will be coming soon.

### Recommended Install Path

Use GitHub clone/local install today. Homebrew support is coming soon.

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/smartshot.git
cd smartshot
scripts/install.sh
scripts/start-app.command
```

Then choose your screenshot folder in the app and click **Start Watching**.
That starts SmartShot's local watcher for the selected screenshot folder.

To run automatically after login:

```bash
scripts/install-background.command
```

To remove background mode:

```bash
scripts/uninstall-background.command
```

Fork the repository on GitHub first if you want your own copy. Then clone your
fork:

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/smartshot.git
cd smartshot
```

Or download the ZIP from GitHub, unzip it, and open Terminal in the project
folder.

Install the local app environment:

```bash
scripts/install.sh
```

Start the local desktop app:

```bash
scripts/start-app.command
```

The app lets users choose a screenshot folder, start or stop watching, rename a
single file, backfill existing screenshots, and install the background watcher.

What is already implemented in this project:

- a Tkinter desktop app launched by `scripts/start-app.command`;
- a CLI entrypoint launched by `.venv/bin/smartshot`;
- local editable installation through `scripts/install.sh`;
- Apple Vision OCR support when the `vision` extra installs successfully;
- background mode through a macOS LaunchAgent.

What is not done yet:

- a double-clickable signed macOS `.app` bundle;
- an app icon;
- notarization/signing;
- a DMG or GitHub Release artifact;
- Homebrew distribution, coming soon;
- PyPI distribution.

## Does It Work After Install?

Not automatically, and that is intentional.

After installation, the user chooses one mode:

- App mode: open SmartShot and click Start Watching. It renames screenshots while
  the app is open.
- Background mode: run `scripts/install-background.command` or click Install
  Background in the app. Then SmartShot runs after login and renames screenshots
  automatically.

Background mode watches `~/Desktop` by default.

To remove background mode:

```bash
scripts/uninstall-background.command
```

## Future Homebrew And Packaged App

A Homebrew version is planned. For now, use the GitHub clone flow above and
start SmartShot locally with:

```bash
scripts/start-app.command
```

After package publishing, a future install path may look like this:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install "smartshot[vision]"
```

Then users would be able to open the desktop app with:

```bash
smartshot-app
```

You can also open the app through the CLI:

```bash
smartshot app
```

If the app says Python Tk support is missing, install a macOS Python build that
includes `tkinter` and reinstall SmartShot. The CLI still works without Tk.

## Command Line

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
. .venv/bin/activate

smartshot backfill --dir ~/Desktop
```

Remove it:

```bash
smartshot uninstall
```

Useful options:

- `--timestamp`: append the screenshot date/time to the filename.
- `--dry-run`: show what would happen without renaming files.
- `--force`: rename even when OCR is empty or unclear.
- `--all-images`: rename any new `.png`, `.jpg`, or `.jpeg`, not only standard macOS screenshots.

## Development

```bash
git clone <repo-url>
cd smartshot
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[vision,dev]"
pytest
```

Build distribution artifacts:

```bash
python -m build
```

## Notes

- If OCR text contains a domain such as `superteam.fun`, SmartShot prefers the
  domain label, such as `superteam`.
- If OCR text contains a filename such as `naming.py`, SmartShot prefers the
  filename stem, such as `naming`.
- A manual LaunchAgent template is available at
  `launchd/com.smartshot.watch.plist`, but most users should use
  `smartshot install`.
