from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env_file(path: Path | None = None) -> None:
    """Load simple KEY=VALUE pairs from a local .env file.

    Existing environment variables win. This intentionally supports only the
    small .env subset SmartShot needs, so secrets stay local without adding a
    runtime dependency.
    """

    env_path = path if path is not None else project_root() / ".env"
    if not env_path.exists():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or key in os.environ:
            continue

        os.environ[key] = value
