from __future__ import annotations

import queue
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError as e:
    _TK_IMPORT_ERROR: ModuleNotFoundError | None = e

    class _TkFallback:
        Tk = object
        BOTH = "both"
        DISABLED = "disabled"
        END = "end"
        LEFT = "left"
        NORMAL = "normal"
        RIGHT = "right"
        W = "w"
        WORD = "word"
        X = "x"
        Y = "y"

    tk = _TkFallback()
    filedialog = None
    messagebox = None
    ttk = None
else:
    _TK_IMPORT_ERROR = None

from .core import rename_image
from .launchd import InstallOptions
from .launchd import install as launchd_install
from .launchd import status as launchd_status
from .launchd import uninstall as launchd_uninstall
from .utils import is_probably_macos_screenshot
from .watcher import WatchOptions, WatchSession


class SmartShotApp(tk.Tk):
    def __init__(self) -> None:
        if _TK_IMPORT_ERROR is not None:
            raise RuntimeError(
                "SmartShot's desktop app requires Python Tk support. "
                "Install a Python build that includes tkinter, or use the CLI "
                "commands such as 'smartshot watch --dir ~/Desktop'."
            ) from _TK_IMPORT_ERROR

        super().__init__()

        self.title("SmartShot")
        self.minsize(760, 520)

        self.folder_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.timestamp_var = tk.BooleanVar(value=False)
        self.all_images_var = tk.BooleanVar(value=False)
        self.force_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Idle")

        self._session: WatchSession | None = None
        self._log_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self._poll_log_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=20)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=tk.X)

        title = ttk.Label(header, text="SmartShot", font=("TkDefaultFont", 24, "bold"))
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            header,
            text="Rename screenshots automatically using OCR.",
        )
        subtitle.pack(anchor=tk.W, pady=(4, 18))

        folder_row = ttk.Frame(root)
        folder_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(folder_row, text="Screenshot folder").pack(anchor=tk.W)

        folder_controls = ttk.Frame(folder_row)
        folder_controls.pack(fill=tk.X, pady=(6, 0))
        folder_entry = ttk.Entry(folder_controls, textvariable=self.folder_var)
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_controls, text="Choose...", command=self._choose_folder).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        options = ttk.LabelFrame(root, text="Options", padding=12)
        options.pack(fill=tk.X, pady=(0, 12))

        ttk.Checkbutton(
            options,
            text="Append timestamp to filename",
            variable=self.timestamp_var,
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 18), pady=4)
        ttk.Checkbutton(
            options,
            text="Watch subfolders",
            variable=self.recursive_var,
        ).grid(row=0, column=1, sticky=tk.W, pady=4)
        ttk.Checkbutton(
            options,
            text="Rename all images",
            variable=self.all_images_var,
        ).grid(row=1, column=0, sticky=tk.W, padx=(0, 18), pady=4)
        ttk.Checkbutton(
            options,
            text="Force unclear OCR",
            variable=self.force_var,
        ).grid(row=1, column=1, sticky=tk.W, padx=(0, 18), pady=4)

        actions = ttk.Frame(root)
        actions.pack(fill=tk.X, pady=(0, 12))

        self.start_button = ttk.Button(actions, text="Start Watching", command=self._start)
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(
            actions,
            text="Stop",
            command=self._stop,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Rename File...", command=self._rename_file).pack(
            side=tk.LEFT,
            padx=(18, 0),
        )
        ttk.Button(actions, text="Backfill Folder", command=self._backfill).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )
        ttk.Button(actions, text="Install Background", command=self._install_background).pack(
            side=tk.RIGHT,
        )
        ttk.Button(actions, text="Remove Background", command=self._uninstall_background).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        status = ttk.Frame(root)
        status.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(status, text="Status:").pack(side=tk.LEFT)
        ttk.Label(status, textvariable=self.status_var).pack(side=tk.LEFT, padx=(6, 0))

        log_frame = ttk.LabelFrame(root, text="Activity", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.configure(yscrollcommand=scrollbar.set)

        self._log("Ready. Choose a folder, then start watching.")

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(
            initialdir=self.folder_var.get() or str(Path.home()),
            title="Choose screenshot folder",
        )
        if selected:
            self.folder_var.set(selected)

    def _options(self) -> WatchOptions:
        return WatchOptions(
            directory=Path(self.folder_var.get()).expanduser(),
            recursive=self.recursive_var.get(),
            force=self.force_var.get(),
            all_images=self.all_images_var.get(),
            include_timestamp=self.timestamp_var.get(),
        )

    def _start(self) -> None:
        try:
            self._session = WatchSession(self._options(), log_callback=self._thread_log)
            self._session.start()
        except Exception as e:
            messagebox.showerror("SmartShot", f"Could not start watcher:\n{e}")
            self._session = None
            return

        self.status_var.set(f"Watching {self.folder_var.get()}")
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self._log("Watching started.")

    def _stop(self) -> None:
        if self._session is not None:
            self._session.stop()
            self._session = None

        self.status_var.set("Idle")
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self._log("Watching stopped.")

    def _rename_file(self) -> None:
        selected = filedialog.askopenfilename(
            initialdir=self.folder_var.get() or str(Path.home()),
            title="Choose screenshot",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg"),
                ("All files", "*"),
            ],
        )
        if not selected:
            return

        path = Path(selected)
        if not self.force_var.get() and not is_probably_macos_screenshot(path):
            messagebox.showinfo(
                "SmartShot",
                "This does not look like a standard macOS screenshot name. "
                "Enable 'Force unclear OCR' to rename it anyway.",
            )
            return

        self._run_worker(lambda: self._rename_one(path))

    def _rename_one(self, path: Path) -> None:
        result = rename_image(
            path,
            force=self.force_var.get(),
            include_timestamp=self.timestamp_var.get(),
        )
        if result is None:
            self._thread_log(f"No rename performed: {path.name}")
            return

        self._thread_log(f"RENAMED: {result.original_path.name} -> {result.new_path.name}")

    def _backfill(self) -> None:
        self._run_worker(self._backfill_current_folder)

    def _backfill_current_folder(self) -> None:
        directory = Path(self.folder_var.get()).expanduser()
        if not directory.exists():
            self._thread_log(f"ERROR: folder does not exist: {directory}")
            return

        renamed = 0
        for path in sorted(directory.iterdir()):
            if not path.is_file():
                continue
            if not self.all_images_var.get() and not is_probably_macos_screenshot(path):
                continue

            result = rename_image(
                path,
                force=self.force_var.get(),
                include_timestamp=self.timestamp_var.get(),
            )
            if result is not None:
                renamed += 1
                self._thread_log(
                    f"RENAMED: {result.original_path.name} -> {result.new_path.name}"
                )

        self._thread_log(f"Backfill complete. Renamed: {renamed}")

    def _install_background(self) -> None:
        try:
            path = launchd_install(
                InstallOptions(
                    watch_dir=Path(self.folder_var.get()).expanduser(),
                    recursive=self.recursive_var.get(),
                    all_images=self.all_images_var.get(),
                    include_timestamp=self.timestamp_var.get(),
                    force=self.force_var.get(),
                )
            )
        except Exception as e:
            messagebox.showerror("SmartShot", f"Could not install background watcher:\n{e}")
            return

        status = launchd_status()
        self._log(f"Background watcher installed: {path}")
        self._log(f"Loaded: {status['loaded']}")

    def _uninstall_background(self) -> None:
        removed = launchd_uninstall()
        self._log("Background watcher removed." if removed else "Background watcher was not installed.")

    def _run_worker(self, target) -> None:
        threading.Thread(target=target, daemon=True).start()

    def _thread_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _poll_log_queue(self) -> None:
        while True:
            try:
                message = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self._log(message)

        self.after(100, self._poll_log_queue)

    def _log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, f"{message}\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _on_close(self) -> None:
        self._stop()
        self.destroy()


def main() -> int:
    try:
        app = SmartShotApp()
    except RuntimeError as e:
        print(e)
        return 1

    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
