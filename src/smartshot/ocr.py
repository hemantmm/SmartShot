from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path


class OcrError(RuntimeError):
    pass


def extract_text(image_path: Path) -> str:
    """Extract text from an image.

    Tries macOS Vision (if available), then falls back to `tesseract` if installed.
    Returns an empty string if no OCR backend is available.
    """

    image_path = Path(image_path)

    if platform.system() == "Darwin":
        vision_text = _try_vision_ocr(image_path)
        if vision_text is not None:
            return vision_text

    tesseract_text = _try_tesseract_ocr(image_path)
    if tesseract_text is not None:
        return tesseract_text

    return ""


def _try_vision_ocr(image_path: Path) -> str | None:
    try:
        from Cocoa import NSURL  # type: ignore
        import Quartz  # type: ignore
        import Vision  # type: ignore
    except Exception:
        return None

    try:
        url = NSURL.fileURLWithPath_(str(image_path))
        source = Quartz.CGImageSourceCreateWithURL(url, None)
        if source is None:
            raise OcrError(f"Could not create image source for: {image_path}")

        cg_image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
        if cg_image is None:
            raise OcrError(f"Could not load image: {image_path}")

        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(True)

        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
            cg_image, {}
        )
        ok, error = handler.performRequests_error_([request], None)
        if not ok or error is not None:
            raise OcrError(str(error) if error is not None else "Vision OCR failed")

        results = request.results() or []
        lines: list[str] = []
        for obs in results:
            candidates = obs.topCandidates_(1)
            if candidates and len(candidates) > 0:
                lines.append(str(candidates[0].string()))

        return "\n".join(lines).strip()
    except Exception:
        # Treat any Vision OCR failure as 'not available' so we can fall back.
        return None


def _try_tesseract_ocr(image_path: Path) -> str | None:
    if shutil.which("tesseract") is None:
        return None

    try:
        # `tesseract input stdout` prints text to stdout.
        proc = subprocess.run(
            ["tesseract", str(image_path), "stdout"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None
        return (proc.stdout or "").strip()
    except Exception:
        return None
