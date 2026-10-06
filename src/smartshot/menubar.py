import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional

import rumps

from .events import ProcessingEvent
from .watcher import WatchOptions, WatchSession

# rumps defaults to a basic logging configuration; we can customize if needed
logger = logging.getLogger(__name__)

APP_NAME = "SmartShot"
BUNDLE_ID = "com.smartshot.app"

def get_app_support_dir() -> Path:
    path = Path("~/Library/Application Support").expanduser() / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_config_path() -> Path:
    return get_app_support_dir() / "config.json"

class SmartShotMenuApp(rumps.App):
    def __init__(self):
        super(SmartShotMenuApp, self).__init__(APP_NAME)
        self.menu = [
            rumps.MenuItem("Status", callback=None),
            None,
            ("Recent Activity", []),
            None,
            rumps.MenuItem("Start Watching", callback=self.start_watching),
            rumps.MenuItem("Stop Watching", callback=self.stop_watching),
            None,
            rumps.MenuItem("Choose Folder...", callback=self.choose_folder),
            rumps.MenuItem("Open Screenshot Folder", callback=self.open_folder),
            None,
            rumps.MenuItem("About SmartShot", callback=self.show_about),
        ]
        
        self.watch_session: Optional[WatchSession] = None
        self.recent_activity: list[ProcessingEvent] = []
        self.max_recent = 5
        
        # Load config
        self.config_data = self.load_config()
        self.watch_dir = Path(self.config_data.get("watch_directory", "~/Desktop")).expanduser()
        
        self.update_ui_state()

    def load_config(self) -> dict:
        path = get_config_path()
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        return {}

    def save_config(self):
        path = get_config_path()
        try:
            with open(path, "w") as f:
                json.dump({"watch_directory": str(self.watch_dir)}, f)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def update_ui_state(self):
        is_running = self.watch_session is not None and self.watch_session.is_running
        
        # Update Status item
        status_item = self.menu["Status"]
        if is_running:
            self.title = "📷"
            status_item.title = f"● Watching {self.watch_dir.name}"
        else:
            self.title = "📷 (Stopped)"
            status_item.title = "○ Not watching"
            
        self.menu["Start Watching"].state = is_running
        self.menu["Stop Watching"].state = not is_running

    def on_processing_event(self, event: ProcessingEvent):
        # Update the UI from the main thread
        rumps.timer(0)(lambda _: self._handle_event_ui(event))

    def _handle_event_ui(self, event: ProcessingEvent):
        status_item = self.menu["Status"]
        is_running = self.watch_session is not None and self.watch_session.is_running
        base_status = f"● Watching {self.watch_dir.name}" if is_running else "○ Not watching"

        if event.status == "detected":
            status_item.title = f"Processing screenshot..."
        elif event.status == "processing":
            status_item.title = f"{event.message}..."
        elif event.status == "ocr_complete":
            status_item.title = f"Generating filename..."
        elif event.status == "renaming":
            status_item.title = f"Renaming..."
        elif event.status in ("completed", "skipped", "error"):
            status_item.title = base_status
            
            # Only add to history if it's a completed rename or an error
            if event.status in ("completed", "error"):
                self.add_recent_activity(event)

    def add_recent_activity(self, event: ProcessingEvent):
        self.recent_activity.insert(0, event)
        if len(self.recent_activity) > self.max_recent:
            self.recent_activity.pop()
            
        self.refresh_recent_activity_menu()

    def refresh_recent_activity_menu(self):
        recent_menu = self.menu["Recent Activity"]
        recent_menu.clear()
        
        if not self.recent_activity:
            recent_menu.add(rumps.MenuItem("No recent activity"))
            return
            
        for event in self.recent_activity:
            if event.status == "completed" and event.new_path:
                title = f"✓ {event.new_path.stem}"
            elif event.status == "error":
                title = f"⚠ Failed: {event.original_path.name if event.original_path else 'Unknown'}"
            else:
                title = f"○ {event.status}"
                
            item = rumps.MenuItem(title, callback=self.on_recent_click)
            item.event = event # attach event data to the item
            recent_menu.add(item)

    def on_recent_click(self, sender):
        event = getattr(sender, "event", None)
        if event and event.new_path and event.new_path.exists():
            subprocess.run(["open", "-R", str(event.new_path)])
        elif event and event.original_path and event.original_path.exists():
            subprocess.run(["open", "-R", str(event.original_path)])
        else:
            rumps.alert("File Not Found", "The screenshot file could not be found.")

    def start_watching(self, _):
        if self.watch_session and self.watch_session.is_running:
            return

        # Test if we actually have permission to read the folder
        try:
            os.listdir(self.watch_dir)
        except PermissionError:
            rumps.alert(
                title="Permission Denied",
                message=f"SmartShot does not have permission to read your {self.watch_dir.name} folder.\n\nPlease go to System Settings > Privacy & Security > Files and Folders (or Full Disk Access), enable access for SmartShot, and try again."
            )
            return
        except Exception as e:
            rumps.alert("Error", f"Could not access {self.watch_dir}: {e}")
            return

        opts = WatchOptions(directory=self.watch_dir)
        self.watch_session = WatchSession(
            opts,
            log_callback=lambda msg: logger.info(msg),
            event_callback=self.on_processing_event
        )
        self.watch_session.start()
        self.update_ui_state()

    def stop_watching(self, _):
        if self.watch_session:
            self.watch_session.stop()
            self.watch_session = None
        self.update_ui_state()

    def choose_folder(self, _):
        # Open macOS folder picker via AppleScript
        script = 'tell application "System Events" to POSIX path of (choose folder with prompt "Select Screenshot Folder:")'
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
            chosen_path = result.stdout.strip()
            if chosen_path:
                was_running = self.watch_session is not None and self.watch_session.is_running
                if was_running:
                    self.stop_watching(None)
                
                self.watch_dir = Path(chosen_path)
                self.save_config()
                
                if was_running:
                    self.start_watching(None)
                else:
                    self.update_ui_state()
        except subprocess.CalledProcessError:
            pass # User cancelled

    def open_folder(self, _):
        if self.watch_dir.exists():
            subprocess.run(["open", str(self.watch_dir)])

    def show_about(self, _):
        rumps.alert(
            title="About SmartShot",
            message="SmartShot\nAutomatically organize your screenshots using OCR-powered smart filenames.\n\nVersion 1.0.0",
            ok="OK"
        )

def main():
    app = SmartShotMenuApp()
    app.run()

if __name__ == "__main__":
    main()
