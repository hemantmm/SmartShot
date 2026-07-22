from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


LABEL = "com.smartshot.watch"


@dataclass(frozen=True)
class InstallOptions:
    watch_dir: Path
    recursive: bool = False
    all_images: bool = False
    include_timestamp: bool = False
    force: bool = False
    stdout_path: Path = Path("/tmp/smartshot.out.log")
    stderr_path: Path = Path("/tmp/smartshot.err.log")
    dry_run: bool = False


def launchagents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def plist_path() -> Path:
    return launchagents_dir() / f"{LABEL}.plist"


def _program_arguments_for_current_install(opts: InstallOptions) -> list[str]:
    # Prefer calling the smartshot entrypoint in the current environment.
    smartshot = shutil.which("smartshot")
    if smartshot:
        base = [smartshot]
    else:
        # Fallback: use python -m smartshot
        base = [sys.executable, "-m", "smartshot"]

    args = base + ["watch", "--dir", str(opts.watch_dir)]

    if opts.recursive:
        args.append("--recursive")

    if opts.all_images:
        args.append("--all-images")

    if opts.include_timestamp:
        args.append("--timestamp")

    if opts.force:
        args.append("--force")

    return args


def generate_plist(program_args: list[str], *, stdout_path: Path, stderr_path: Path) -> bytes:
    plist = {
        "Label": LABEL,
        "ProgramArguments": program_args,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "StandardOutPath": str(stdout_path),
        "StandardErrorPath": str(stderr_path),
    }

    return plistlib.dumps(plist)


def is_installed() -> bool:
    return plist_path().exists()


def install(opts: InstallOptions) -> Path:
    opts_dir = Path(opts.watch_dir).expanduser().resolve()

    la_dir = launchagents_dir()
    la_dir.mkdir(parents=True, exist_ok=True)

    args = _program_arguments_for_current_install(InstallOptions(**{**opts.__dict__, "watch_dir": opts_dir}))
    data = generate_plist(args, stdout_path=opts.stdout_path, stderr_path=opts.stderr_path)

    dest = plist_path()
    dest.write_bytes(data)

    if not opts.dry_run:
        _launchctl_bootout_if_loaded(dest)
        _launchctl_bootstrap(dest)
        _launchctl_kickstart()

    return dest


def uninstall(*, dry_run: bool = False) -> bool:
    path = plist_path()
    existed = path.exists()

    if existed and not dry_run:
        _launchctl_bootout_if_loaded(path)

    if existed:
        try:
            path.unlink(missing_ok=True)
        except TypeError:
            # Python < 3.8 compatibility not needed, but keep safe.
            if path.exists():
                path.unlink()

    return existed


def status() -> dict[str, str | bool]:
    path = plist_path()
    installed = path.exists()
    loaded = False

    if installed:
        loaded = _launchctl_is_loaded()

    return {
        "installed": installed,
        "loaded": loaded,
        "plist": str(path),
        "label": LABEL,
    }


def _launchctl_domain() -> str:
    # Per-user GUI domain
    return f"gui/{os.getuid()}"


def _run_launchctl(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["launchctl", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _launchctl_is_loaded() -> bool:
    # `launchctl print gui/UID/LABEL` returns 0 if loaded.
    proc = _run_launchctl(["print", f"{_launchctl_domain()}/{LABEL}"])
    return proc.returncode == 0


def _launchctl_bootstrap(plist: Path) -> None:
    proc = _run_launchctl(["bootstrap", _launchctl_domain(), str(plist)])
    if proc.returncode != 0:
        # Fall back to deprecated load (some setups still rely on it)
        proc2 = _run_launchctl(["load", "-w", str(plist)])
        if proc2.returncode != 0:
            raise RuntimeError(
                "Failed to load LaunchAgent. "
                f"bootstrap: {proc.stderr.strip()} | load: {proc2.stderr.strip()}"
            )


def _launchctl_bootout_if_loaded(plist: Path) -> None:
    # Try modern command first.
    proc = _run_launchctl(["bootout", _launchctl_domain(), str(plist)])
    if proc.returncode == 0:
        return

    # Fall back to deprecated unload.
    _run_launchctl(["unload", str(plist)])


def _launchctl_kickstart() -> None:
    # Start (or restart) the agent now.
    proc = _run_launchctl(["kickstart", "-k", f"{_launchctl_domain()}/{LABEL}"])
    if proc.returncode != 0:
        # Not fatal: it may still start at load.
        return
