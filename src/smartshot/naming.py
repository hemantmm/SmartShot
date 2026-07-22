from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from collections import Counter

from .utils import parse_timestamp_from_macos_screenshot_name


@dataclass(frozen=True)
class NameSuggestion:
    summary: str
    timestamp: datetime


_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b",
    re.IGNORECASE,
)

_URL_WITH_PATH_RE = re.compile(
    r"\b(?P<domain>(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,})"
    r"(?P<path>/[^\s]*)",
    re.IGNORECASE,
)

_FILENAME_TOKEN_RE = re.compile(
    r"\b[\w.-]+\.(?:py|js|ts|tsx|jsx|java|kt|go|rs|swift|rb|php|cs|cpp|c|h|hpp|md|txt|json|ya?ml|toml|ini|env|sql|html|css|scss)\b",
    re.IGNORECASE,
)

# Minimal handling for common 2-level public suffixes.
_COMMON_2LEVEL_SUFFIXES = {
    "co.uk",
    "com.au",
    "co.in",
    "co.jp",
    "com.br",
    "co.nz",
    "co.za",
}


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "before",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "else",
    "for",
    "from",
    "go",
    "had",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "like",
    "may",
    "might",
    "more",
    "most",
    "not",
    "of",
    "often",
    "on",
    "or",
    "other",
    "our",
    "previous",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "those",
    "to",
    "too",
    "under",
    "up",
    "update",
    "updates",
    "use",
    "using",
    "visit",
    "workload",
    "workloads",
    "vs",
    "v",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "why",
    "will",
    "with",
    "without",
    "would",
    "you",
}

_UI_LABELS = {
    "chrome",
    "chrome file",
    "file",
    "edit",
    "view",
    "history",
    "bookmarks",
    "blog",
    "profiles",
    "safari",
    "discussion",
    "tab",
    "tab window",
    "window",
    "help",
    "medium",
    "search",
    "get app",
    "write",
    "sign up",
    "sign in",
}

_GENERIC_SINGLE_WORDS = {
    "data",
    "dataset",
    "datasets",
    "image",
    "latency",
    "page",
    "read",
    "reads",
    "screenshot",
    "time",
    "window",
    "write",
    "writes",
}

_DIAGRAM_LABEL_PREFIXES = (
    "active interval",
    "event bucket",
    "event buckets",
    "future interval",
    "ideal latency",
    "other event buckets",
    "past retention",
    "t = time",
    "t=time",
    "table_",
    "time bucket",
    "time buckets",
    "time slices",
)

_SLUG_STOPWORDS = _STOPWORDS | {
    "dynamically",
    "splitting",
}

_KNOWN_SHORT_ACRONYMS = {
    "AI",
    "API",
    "CI",
    "CD",
    "CPU",
    "CSS",
    "DB",
    "DNS",
    "GPU",
    "HTML",
    "HTTP",
    "HTTPS",
    "ID",
    "IP",
    "JSON",
    "ML",
    "OCR",
    "PR",
    "SQL",
    "UI",
    "URL",
}

_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]{1,}\b")


def compact_topic(text: str, *, max_words: int = 4) -> str:
    """Return a short, searchable topic phrase (1–max_words).

    Intended for screenshot filenames: prefer headings / distinctive tokens over
    full sentences.
    """

    max_words = max(1, int(max_words))
    if not text or not text.strip():
        return ""

    file_token = _extract_preferred_filename_token(text)
    if file_token:
        return file_token

    source_label = source_label_from_ocr(text)
    cleaned_text = clean_ocr_for_naming(text)
    text_without_domains = _DOMAIN_RE.sub(" ", cleaned_text)

    # 1) Prefer visible content headings over browser address-bar domains.
    heading = _best_heading_line(cleaned_text)
    if heading:
        words = _keywords_from_line(heading)
        if words:
            topic = _join_topic_words(words, max_words=max_words)
            return topic

    # 2) Prefer a readable article/page slug over diagram labels when the
    # visible heading was missed by OCR.
    slug_topic = _topic_from_url_slug(text, max_words=max_words)
    if slug_topic:
        return _with_source(slug_topic, source_label)

    # 3) Fall back to keyword scoring across the whole OCR text.
    words = _best_keywords(text_without_domains, max_words=max_words)
    if words:
        topic = " ".join(words)
        return _with_source(topic, source_label)

    # 4) Last resort: attempt to extract from the best single line.
    line = _best_summary_line(cleaned_text)
    if line:
        words = _best_keywords(_DOMAIN_RE.sub(" ", line), max_words=max_words)
        if words:
            topic = " ".join(words)
            return _with_source(topic, source_label)

    if source_label:
        return source_label

    return ""


def clean_ocr_for_naming(text: str) -> str:
    """Remove common browser/app chrome OCR noise before naming."""

    if not text:
        return ""

    kept: list[str] = []
    for raw_line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", raw_line).strip()
        if not cleaned:
            continue
        if _is_noise_line(cleaned):
            continue
        kept.append(cleaned)

    return "\n".join(kept)


def source_label_from_ocr(text: str) -> str:
    return _extract_preferred_source_label(text)


def is_low_quality_summary(text: str) -> bool:
    cleaned = sanitize_filename_component(text).strip()
    if not cleaned:
        return True

    low = cleaned.lower()
    if low in _UI_LABELS or low in _GENERIC_SINGLE_WORDS:
        return True

    # Reject "time by Netflix", "Tab Window by Netflix", etc. The source is
    # useful only if the topic before it is useful.
    topic_without_source = re.sub(r"\s+by\s+[a-z0-9 ._-]+$", "", low).strip()
    if topic_without_source in _UI_LABELS or topic_without_source in _GENERIC_SINGLE_WORDS:
        return True

    words = _keywords_from_line(cleaned)
    if words and words[0].lower() in _GENERIC_SINGLE_WORDS and len(words) <= 2:
        return True
    if len(words) == 1 and words[0].lower() in _GENERIC_SINGLE_WORDS:
        return True
    if len(words) <= 2 and all(w.lower() in _UI_LABELS for w in words):
        return True

    return False


def suggest_name(image_path: Path, ocr_text: str) -> NameSuggestion:
    image_path = Path(image_path)

    timestamp = parse_timestamp_from_macos_screenshot_name(image_path.stem)
    if timestamp is None:
        try:
            timestamp = datetime.fromtimestamp(image_path.stat().st_mtime)
        except Exception:
            timestamp = datetime.now()

    summary = compact_topic(ocr_text, max_words=4)
    summary = sanitize_filename_component(summary, max_len=80)

    if not summary:
        summary = "screenshot"

    return NameSuggestion(summary=summary, timestamp=timestamp)


def format_new_stem(s: NameSuggestion) -> str:
    return format_new_stem_with_options(s, include_timestamp=True)


def format_new_stem_with_options(
    s: NameSuggestion, *, include_timestamp: bool = True
) -> str:
    if not include_timestamp:
        return s.summary

    # Keep the familiar macOS time style but put the summary first.
    ts = s.timestamp.strftime("%Y-%m-%d at %H.%M.%S")
    return f"{s.summary} - {ts}"


def _best_summary_line(text: str) -> str:
    if not text:
        return ""

    # Normalize whitespace and split into lines.
    raw_lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in raw_lines if ln]

    if not lines:
        # fallback: single-line from whitespace collapse
        collapsed = re.sub(r"\s+", " ", text).strip()
        return collapsed

    scored: list[tuple[int, str]] = []
    for ln in lines:
        cleaned = re.sub(r"\s+", " ", ln).strip()
        if not cleaned:
            continue

        if len(cleaned) < 4:
            continue

        has_alpha = any(ch.isalpha() for ch in cleaned)
        if not has_alpha:
            continue

        score = 0
        length = len(cleaned)
        if 10 <= length <= 70:
            score += 10
        elif length <= 100:
            score += 5
        else:
            score -= 5

        words = cleaned.split(" ")
        alpha_words = sum(1 for w in words if any(ch.isalpha() for ch in w))
        digit_chars = sum(1 for ch in cleaned if ch.isdigit())

        score += min(alpha_words, 12)
        if digit_chars > max(6, length // 2):
            score -= 6

        if cleaned.lower().startswith("screenshot"):
            score -= 10

        scored.append((score, cleaned))

    if not scored:
        return ""

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _extract_preferred_filename_token(text: str) -> str:
    if not text:
        return ""

    # Prefer shorter filenames, not paths.
    found: list[str] = []
    for match in _FILENAME_TOKEN_RE.finditer(text):
        token = match.group(0).strip()
        if not token:
            continue
        # If OCR accidentally includes a path, take the final segment.
        token = token.split("/")[-1].split("\\")[-1]
        token = token.strip(". ")
        if not token:
            continue
        if token not in found:
            found.append(token)

    if not found:
        return ""

    # Choose the shortest token (usually the clean filename, e.g. naming.py)
    found.sort(key=lambda s: (len(s), s.lower()))
    token = found[0]

    # Screenshots already have an image extension; drop the code/doc extension.
    stem = Path(token).stem
    return stem.strip(". ")


def _extract_preferred_source_label(text: str) -> str:
    if not text:
        return ""

    found: list[str] = []
    for match in _DOMAIN_RE.finditer(text):
        domain = match.group(0).strip().strip(".").lower()
        if not domain:
            continue
        if domain not in found:
            found.append(domain)

    for domain in found:
        label = _domain_to_label(domain)
        if not label:
            continue
        label = _clean_source_label(label)

        # Filter obvious non-names.
        if label in {"www", "local", "localhost"}:
            continue
        if len(label) < 3:
            continue
        if label.isdigit():
            continue

        return label

    return ""


def _is_noise_line(line: str) -> bool:
    low = line.lower().strip()
    if not low:
        return True

    if low in _UI_LABELS:
        return True

    words = [w.lower() for w in re.findall(r"[A-Za-z]+", line)]
    if words and all(w in _UI_LABELS for w in words):
        return True

    if len(words) == 1 and words[0] in _GENERIC_SINGLE_WORDS:
        return True
    if any(low.startswith(prefix) for prefix in _DIAGRAM_LABEL_PREFIXES):
        return True
    if low.startswith("here is what "):
        return True
    if re.search(r"\s[-–—]\s*tutorial$", low):
        return True

    # Browser tabs can leak clipped titles like "You jus", "Allow tc", or
    # "feat(sy" into OCR. They are short, early, and otherwise look title-ish.
    if len(line) <= 14:
        if low.startswith(("feat(", "feat ", "new ta", "you ")):
            return True
        if len(words) == 2 and words[0] == "allow" and len(words[1]) <= 4:
            return True

    if _DOMAIN_RE.search(line) or "://" in line:
        return True

    # macOS menu/status OCR often appears as date/time/battery fragments.
    if re.search(r"\b(?:mon|tue|wed|thu|fri|sat|sun)\b", low) and re.search(
        r"\d{1,2}:\d{2}", low
    ):
        return True
    if re.fullmatch(r"\d{1,3}%", low):
        return True

    return False


def _clean_source_label(label: str) -> str:
    label = label.strip().lower()
    if label.endswith("techblog") and len(label) > len("techblog"):
        label = label[: -len("techblog")]
    if label.endswith("blog") and len(label) > len("blog"):
        label = label[: -len("blog")]

    known = {
        "github": "GitHub",
        "netflix": "Netflix",
        "medium": "Medium",
        "stripe": "Stripe",
    }
    return known.get(label, label)


def _topic_from_url_slug(text: str, *, max_words: int) -> str:
    if not text:
        return ""

    for match in _URL_WITH_PATH_RE.finditer(text):
        path = match.group("path")
        path = path.split("?", 1)[0].split("#", 1)[0]
        parts = [p for p in path.split("/") if p]
        if not parts:
            continue

        slug = max(parts, key=len)
        slug = re.sub(r"[-_]+", " ", slug)
        words = []
        for raw in re.findall(r"[A-Za-z][A-Za-z0-9]+", slug):
            low = raw.lower()
            if low in _SLUG_STOPWORDS:
                continue
            if re.fullmatch(r"[a-f0-9]{8,}", low):
                continue
            words.append(raw)

        if not words:
            continue

        phrase = _slug_words_to_topic(words, max_words=max_words)
        if phrase:
            return phrase

    return ""


def _slug_words_to_topic(words: list[str], *, max_words: int) -> str:
    lowered = [w.lower() for w in words]

    # Common article-title pattern from technical blogs. Keep the phrase users
    # will remember instead of generic words like "workloads".
    if "time" in lowered and "series" in lowered:
        if "partitions" in lowered or "partitioning" in lowered:
            return "Time Series Partitions"
        return "Time Series"

    chosen = []
    for word in words:
        low = word.lower()
        if low in _GENERIC_SINGLE_WORDS:
            continue
        chosen.append(word.capitalize())
        if len(chosen) >= max_words:
            break

    return " ".join(chosen)


def _with_source(topic: str, source_label: str) -> str:
    topic = topic.strip()
    source_label = source_label.strip()
    if not topic:
        return source_label
    if not source_label:
        return topic
    if source_label.lower() in topic.lower():
        return topic
    return f"{topic} by {source_label}"


def _domain_to_label(domain: str) -> str:
    labels = [p for p in domain.split(".") if p]
    if len(labels) < 2:
        return domain

    if len(labels) >= 3:
        suffix2 = ".".join(labels[-2:])
        if suffix2 in _COMMON_2LEVEL_SUFFIXES:
            return labels[-3]

    return labels[-2]


def sanitize_filename_component(text: str, *, max_len: int = 80) -> str:
    # Cross-platform safety: remove reserved characters.
    # Windows reserved: <>:"/\|?*
    reserved = r'<>:"/\\|\?\*'

    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")

    normalized = re.sub(f"[{reserved}]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Keep words, punctuation that is generally safe.
    normalized = re.sub(r"[^a-zA-Z0-9 .,_\-+()\[\]]+", "", normalized).strip()

    if len(normalized) > max_len:
        normalized = normalized[:max_len].rstrip()

    # Avoid trailing dots/spaces (problematic on some filesystems).
    return normalized.rstrip(" .")


def _best_heading_line(text: str) -> str:
    raw_lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in raw_lines if ln]
    if not lines:
        return ""

    candidates: list[tuple[int, str]] = []
    for idx, ln in enumerate(lines[:20]):
        cleaned = re.sub(r"\s+", " ", ln).strip()
        if not cleaned:
            continue

        if cleaned.lower().startswith("screenshot"):
            continue
        if _DOMAIN_RE.search(cleaned) or "://" in cleaned:
            continue

        # Headings are typically short-ish.
        if len(cleaned) < 4 or len(cleaned) > 70:
            continue

        words = cleaned.split(" ")
        if len(words) == 1 and len(words[0]) <= 3:
            continue
        if len(words) > 8:
            continue

        # Skip lines that look like a plain sentence (end with a period).
        if cleaned.endswith(".") and len(words) >= 6:
            continue

        score = 0
        # Prefer early lines.
        score += max(0, 20 - idx * 2)
        # Question/colon headings.
        if cleaned.endswith("?"):
            score += 8
        if cleaned.endswith(":"):
            score += 5

        # Reward title-case / acronyms.
        titleish = 0
        for w in words:
            w2 = re.sub(r"[^A-Za-z0-9]", "", w)
            if not w2:
                continue
            if w2 in _KNOWN_SHORT_ACRONYMS:
                titleish += 2
            elif w2[0].isupper():
                titleish += 1

        if titleish == 0 and not cleaned.endswith(("?", ":")):
            continue

        score += min(titleish, 8)
        if len(words) >= 2:
            score += 8
        if len(words) >= 3:
            score += 5

        # Penalize obvious filler words.
        lower = cleaned.lower()
        if lower in _UI_LABELS:
            continue
        if lower.startswith("before we"):
            score -= 8

        candidates.append((score, cleaned))

    if not candidates:
        return ""

    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]


def _keywords_from_line(line: str) -> list[str]:
    tokens: list[str] = []
    for m in _WORD_RE.finditer(line):
        tok = m.group(0)
        low = tok.lower()
        if low in _STOPWORDS:
            continue
        if len(tok) < 3 and not tok.isupper():
            continue
        tokens.append(tok)

    return tokens


def _is_camelcase(token: str) -> bool:
    return any(ch.islower() for ch in token) and any(ch.isupper() for ch in token[1:])


def _token_key(token: str) -> str:
    # Lowercase key for counting, but keep alnum only for stability.
    return re.sub(r"[^a-z0-9]", "", token.lower())


def _best_keywords(text: str, *, max_words: int) -> list[str]:
    max_words = max(1, int(max_words))
    matches = list(_WORD_RE.finditer(text))
    if not matches:
        return []

    # Collect tokens with positions.
    keyed: list[tuple[str, str, int]] = []  # (key, original, pos)
    for m in matches:
        tok = m.group(0)
        low = tok.lower()
        if low in _STOPWORDS:
            continue

        # Keep known short acronyms, but drop most tiny OCR noise.
        if len(tok) < 3 and tok.upper() not in _KNOWN_SHORT_ACRONYMS:
            continue
        if tok.isupper() and len(tok) <= 3 and tok not in _KNOWN_SHORT_ACRONYMS:
            continue

        if tok.isdigit():
            continue

        key = _token_key(tok)
        if not key:
            continue

        # Filter very generic web tokens.
        if key in {"http", "https", "www", "com", "org", "net"}:
            continue

        keyed.append((key, tok, m.start()))

    if not keyed:
        return []

    counts = Counter(k for (k, _tok, _pos) in keyed)
    first_seen: dict[str, tuple[str, int]] = {}
    for k, tok, pos in keyed:
        if k not in first_seen or pos < first_seen[k][1]:
            first_seen[k] = (tok, pos)

    scored: list[tuple[float, str]] = []  # (score, key)
    for k, cnt in counts.items():
        tok, pos = first_seen[k]

        score = float(cnt) * 2.0
        if tok in _KNOWN_SHORT_ACRONYMS:
            score += 6.0
        elif _is_camelcase(tok):
            score += 7.0
        elif tok[0].isupper():
            score += 2.0

        # Earlier appearance gets a small bonus.
        score += max(0.0, 3.0 - (pos / 200.0))

        # Prefer moderately long words.
        score += min(len(tok), 12) / 8.0

        scored.append((score, k))

    scored.sort(key=lambda t: t[0], reverse=True)

    # Pick the best token; optionally add a second if it's similarly strong.
    best_key = scored[0][1]
    best_tok, _ = first_seen[best_key]
    best_score = scored[0][0]
    best_cnt = counts[best_key]

    words: list[str] = [best_tok]

    if max_words >= 2:
        # If the top token is a known acronym, prefer a single-word filename.
        if best_tok in _KNOWN_SHORT_ACRONYMS and best_cnt >= 1:
            return words

        for score, k in scored[1:]:
            if k == best_key:
                continue
            tok, _pos = first_seen[k]
            if tok.lower() in _STOPWORDS:
                continue
            # Only add if close in relevance.
            if score >= best_score * 0.85:
                words.append(tok)
            break

    return words[:max_words]


def _join_topic_words(words: list[str], *, max_words: int) -> str:
    if not words:
        return ""

    max_words = max(1, int(max_words))

    # Keep a short object after a product/app name when it adds search value,
    # e.g. "GitHub Issue" is more useful than just "GitHub".
    first = words[0]
    if _is_camelcase(first) and max_words >= 2:
        return " ".join(words[:max_words])
    if _is_camelcase(first):
        return first

    # Acronyms are often ambiguous; keep a second word if available.
    if first in _KNOWN_SHORT_ACRONYMS and max_words >= 2 and len(words) >= 2:
        return f"{first} {words[1]}"
    if first in _KNOWN_SHORT_ACRONYMS:
        return first

    return " ".join(words[:max_words])
