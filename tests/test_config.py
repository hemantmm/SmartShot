from __future__ import annotations

import os

from smartshot.config import load_env_file


def test_load_env_file_sets_missing_values(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SMARTSHOT_SAMPLE_KEY=test-key\nSMARTSHOT_MODE=test-mode\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SMARTSHOT_SAMPLE_KEY", raising=False)
    monkeypatch.delenv("SMARTSHOT_MODE", raising=False)

    load_env_file(env_file)

    assert os.environ["SMARTSHOT_SAMPLE_KEY"] == "test-key"
    assert os.environ["SMARTSHOT_MODE"] == "test-mode"


def test_load_env_file_does_not_override_existing_values(monkeypatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SMARTSHOT_SAMPLE_KEY=file-key\n", encoding="utf-8")
    monkeypatch.setenv("SMARTSHOT_SAMPLE_KEY", "existing-key")

    load_env_file(env_file)

    assert os.environ["SMARTSHOT_SAMPLE_KEY"] == "existing-key"
