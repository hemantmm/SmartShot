from __future__ import annotations

import smartshot.app
from smartshot.cli import main


def test_app_module_exposes_main() -> None:
    assert callable(smartshot.app.main)


def test_cli_help_includes_app_command(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit:
        pass

    out = capsys.readouterr().out
    assert "app" in out
    assert "watch" in out
