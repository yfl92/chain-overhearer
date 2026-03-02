"""
detector.py — Detect human-readable English or Chinese messages in EVM calldata.
"""

import string
from langdetect import detect, LangDetectException

MIN_PRINTABLE_CHARS = 10
MIN_PRINTABLE_RATIO = 0.70
ACCEPTED_LANGUAGES = {"en", "zh-cn", "zh-tw"}


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    printable = sum(1 for c in text if c in string.printable or "\u4e00" <= c <= "\u9fff")
    return printable / len(text)


def _try_decode(data: bytes) -> str | None:
    try:
        return data.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return None


def extract_message(calldata: bytes) -> tuple[str, str] | None:
    """
    Try to extract a human-readable English or Chinese message from calldata.

    Returns (text, language) if a qualifying message is found, else None.
    """
    if not calldata:
        return None

    candidates = [calldata]
    # Also try stripping the 4-byte function selector
    if len(calldata) > 4:
        candidates.append(calldata[4:])

    best: tuple[str, str] | None = None
    best_ratio = 0.0

    for chunk in candidates:
        text = _try_decode(chunk)
        if text is None:
            continue

        ratio = _printable_ratio(text)
        printable_count = sum(
            1 for c in text if c in string.printable or "\u4e00" <= c <= "\u9fff"
        )

        if printable_count < MIN_PRINTABLE_CHARS or ratio < MIN_PRINTABLE_RATIO:
            continue

        try:
            lang = detect(text)
        except LangDetectException:
            continue

        # Normalize zh-cn / zh-tw variants
        if lang.startswith("zh"):
            lang = lang  # keep as-is, both accepted
        if lang not in ACCEPTED_LANGUAGES:
            continue

        if ratio > best_ratio:
            best_ratio = ratio
            best = (text.strip(), lang)

    return best
