from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .core import rename_image
from .utils import is_probably_macos_screenshot


@dataclass(frozen=True)
class WatchOptions:
    directory: Path
    recursive: bool = False
    dry_run: bool = False
    force: bool = False
    all_images: bool = False
    include_timestamp: bool = False


WatchLogCallback = Callable[[str], None]


class _ScreenshotHandler(FileSystemEventHandler):
    def __init__(
        self,
        opts: WatchOptions,
        *,
        log_callback: WatchLogCallback | None = None,
    ) -> None:
        self._opts = opts
        self._log_callback = log_callback
        self._lock = threading.Lock()
        self._recent: dict[Path, float] = {}

    def on_created(self, event):
        if event.is_directory:
            return
        self._maybe_process(Path(event.src_path))

    def on_moved(self, event):
        if event.is_directory:
            return
        self._maybe_process(Path(event.dest_path))

    def _maybe_process(self, path: Path) -> None:
        # Debounce duplicate events.
        now = time.time()
        with self._lock:
            last = self._recent.get(path)
            if last is not None and (now - last) < 2.0:
                return
            self._recent[path] = now

        if not path.exists() or not path.is_file():
            return

        if not self._opts.all_images and not is_probably_macos_screenshot(path):
            return

        try:
            result = rename_image(
                path,
                dry_run=self._opts.dry_run,
                force=self._opts.force,
                include_timestamp=self._opts.include_timestamp,
            )
            if result:
                prefix = "DRY-RUN" if self._opts.dry_run else "RENAMED"
                self._log(
                    f"{prefix}: {result.original_path.name} -> "
                    f"{result.new_path.name}"
                )
        except Exception as e:
            # Best-effort background behavior; errors should not crash the watcher.
            self._log(f"ERROR: {path.name}: {e}")
            return

    def _log(self, message: str) -> None:
        if self._log_callback is not None:
            self._log_callback(message)
        else:
            print(message)


class WatchSession:
    """Manage a watchdog observer for GUI and programmatic callers."""

    def __init__(
        self,
        opts: WatchOptions,
        *,
        log_callback: WatchLogCallback | None = None,
    ) -> None:
        directory = Path(opts.directory).expanduser().resolve()
        self.opts = WatchOptions(**{**opts.__dict__, "directory": directory})
        self._log_callback = log_callback
        self._observer: Observer | None = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def start(self) -> None:
        if self.is_running:
            return

        self.opts.directory.mkdir(parents=True, exist_ok=True)
        handler = _ScreenshotHandler(
            self.opts,
            log_callback=self._log_callback,
        )
        observer = Observer()
        observer.schedule(handler, str(self.opts.directory), recursive=self.opts.recursive)
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        observer = self._observer
        if observer is None:
            return

        observer.stop()
        observer.join()
        self._observer = None


def watch(opts: WatchOptions) -> None:
    session = WatchSession(opts)
    session.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        session.stop()
