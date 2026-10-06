from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class ProcessingEvent:
    status: str
    original_path: Optional[Path] = None
    new_path: Optional[Path] = None
    message: Optional[str] = None
