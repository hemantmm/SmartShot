from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import rename_image
from .launchd import InstallOptions
from .launchd import install as launchd_install
from .launchd import status as launchd_status
from .launchd import uninstall as launchd_uninstall
from .utils import is_probably_macos_screenshot
from .watcher import WatchOptions, watch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="smartshot",
        description="Rename macOS screenshots based on their content using OCR.",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_watch = sub.add_parser("watch", help="Watch a folder and auto-rename new screenshots")
    p_watch.add_argument(
        "--dir",
        default=str(Path.home() / "Desktop"),
        help="Directory to watch (default: ~/Desktop)",
    )
    p_watch.add_argument("--recursive", action="store_true", help="Watch subfolders")
    p_watch.add_argument(
        "--all-images",
        action="store_true",
        help="Rename any new .png/.jpg (not only 'Screenshot …')",
    )
    p_watch.add_argument(
        "--timestamp",
        action="store_true",
        help="Append the screenshot date/time to the filename",
    )
    p_watch.add_argument(
        "--no-timestamp",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p_watch.add_argument("--dry-run", action="store_true", help="Print actions only")
    p_watch.add_argument(
        "--force",
        action="store_true",
        help="Rename even when OCR is empty/unclear (fallback name: 'screenshot')",
    )

    p_rename = sub.add_parser("rename", help="Rename a single screenshot file")
    p_rename.add_argument("path", help="Path to a screenshot image")
    p_rename.add_argument("--timestamp", action="store_true")
    p_rename.add_argument("--no-timestamp", action="store_true", help=argparse.SUPPRESS)
    p_rename.add_argument("--dry-run", action="store_true")
    p_rename.add_argument("--force", action="store_true")

    p_backfill = sub.add_parser(
        "backfill", help="Rename existing screenshots in a folder"
    )
    p_backfill.add_argument(
        "--dir",
        default=str(Path.home() / "Desktop"),
        help="Directory to scan (default: ~/Desktop)",
    )
    p_backfill.add_argument("--timestamp", action="store_true")
    p_backfill.add_argument("--no-timestamp", action="store_true", help=argparse.SUPPRESS)
    p_backfill.add_argument("--dry-run", action="store_true")
    p_backfill.add_argument("--force", action="store_true")

    p_install = sub.add_parser(
        "install",
        help="Install a background LaunchAgent so renaming works automatically",
    )
    p_install.add_argument(
        "--dir",
        default=str(Path.home() / "Desktop"),
        help="Directory to watch (default: ~/Desktop)",
    )
    p_install.add_argument("--recursive", action="store_true")
    p_install.add_argument("--all-images", action="store_true")
    p_install.add_argument("--timestamp", action="store_true")
    p_install.add_argument("--no-timestamp", action="store_true", help=argparse.SUPPRESS)
    p_install.add_argument("--force", action="store_true")
    p_install.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the plist but do not load it",
    )

    p_uninstall = sub.add_parser(
        "uninstall", help="Remove the background LaunchAgent"
    )
    p_uninstall.add_argument("--dry-run", action="store_true")

    sub.add_parser("status", help="Show whether the LaunchAgent is installed")
    sub.add_parser("app", help="Open the SmartShot desktop app")

    args = parser.parse_args(argv)

    if args.cmd == "watch":
        opts = WatchOptions(
            directory=Path(args.dir),
            recursive=bool(args.recursive),
            dry_run=bool(args.dry_run),
            force=bool(args.force),
            all_images=bool(args.all_images),
            include_timestamp=bool(args.timestamp),
        )
        print(f"Watching: {Path(args.dir).expanduser().resolve()}")
        watch(opts)
        return 0

    if args.cmd == "rename":
        path = Path(args.path).expanduser().resolve()
        if not args.force and not is_probably_macos_screenshot(path):
            print(
                "Not a standard macOS screenshot name. Use --force or use 'watch --all-images'.",
                file=sys.stderr,
            )
            return 2

        result = rename_image(
            path,
            dry_run=bool(args.dry_run),
            force=bool(args.force),
            include_timestamp=bool(args.timestamp),
        )
        if not result:
            print("No rename performed.")
            return 0

        prefix = "DRY-RUN" if args.dry_run else "RENAMED"
        print(f"{prefix}: {result.original_path.name} -> {result.new_path.name}")
        return 0

    if args.cmd == "backfill":
        directory = Path(args.dir).expanduser().resolve()
        if not directory.exists():
            print(f"Directory does not exist: {directory}", file=sys.stderr)
            return 2

        renamed = 0
        for path in sorted(directory.iterdir()):
            if not path.is_file():
                continue
            if not args.force and not is_probably_macos_screenshot(path):
                continue

            result = rename_image(
                path,
                dry_run=bool(args.dry_run),
                force=bool(args.force),
                include_timestamp=bool(args.timestamp),
            )
            if result:
                renamed += 1
                prefix = "DRY-RUN" if args.dry_run else "RENAMED"
                print(
                    f"{prefix}: {result.original_path.name} -> {result.new_path.name}"
                )

        print(f"Done. Renamed: {renamed}")
        return 0

    if args.cmd == "install":
        opts = InstallOptions(
            watch_dir=Path(args.dir),
            recursive=bool(args.recursive),
            all_images=bool(args.all_images),
            include_timestamp=bool(args.timestamp),
            force=bool(args.force),
            dry_run=bool(args.dry_run),
        )

        try:
            path = launchd_install(opts)
        except Exception as e:
            print(f"Install failed: {e}", file=sys.stderr)
            return 1

        if args.dry_run:
            print(f"Wrote LaunchAgent plist (not loaded): {path}")
        else:
            print(f"Installed + loaded LaunchAgent: {path}")
            print("Logs: /tmp/smartshot.out.log /tmp/smartshot.err.log")
        return 0

    if args.cmd == "uninstall":
        removed = launchd_uninstall(dry_run=bool(args.dry_run))
        if not removed:
            print("LaunchAgent not installed.")
            return 0
        if args.dry_run:
            print("Would remove LaunchAgent.")
        else:
            print("Removed LaunchAgent.")
        return 0

    if args.cmd == "status":
        st = launchd_status()
        print(f"Installed: {st['installed']}")
        print(f"Loaded: {st['loaded']}")
        print(f"Plist: {st['plist']}")
        return 0

    if args.cmd == "app":
        from .app import main as app_main

        return app_main()

    return 2
