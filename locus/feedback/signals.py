"""Disagreement signal classifier for inferred feedback.

Spec: spec/inferred-feedback.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SignalResult:
    quality: str        # "fail" | "partial"
    confidence: float   # 0.0–1.0
    matched_pattern: str


# Patterns are matched against lowercased, stripped text.
# Order matters within each group — more specific patterns first.

_FAIL_EXACT: list[str] = [
    "that's wrong",
    "that is wrong",
    "that's incorrect",
    "that is incorrect",
    "that's not right",
    "that is not right",
    "you got that wrong",
    "wrong answer",
    "not correct",
    "incorrect",
]

_FAIL_PREFIX: list[str] = [
    "no, that",
]

_PARTIAL_EXACT: list[str] = [
    "not quite",
    "almost, but",
    "close, but",
    "almost right",
    "you missed",
    "you're missing",
    "that's not complete",
    "that is not complete",
    "incomplete answer",
    "that didn't answer",
    "that doesn't answer my question",
    "doesn't answer my question",
    "not what i asked",
    "try again",
    "that's only part",
    "that is only part",
]

_PARTIAL_PREFIX: list[str] = [
    "actually,",
    "actually ",
    "not what i",
    "not what I",
]

_FALSE_POSITIVE_PATTERNS = [
    r"https?://",            # URL
    r"```",                  # code block
    r"`[^`]+`",              # inline code
    r"\./|\.\./",            # file path
    r"^/[a-z]",              # slash command
]
_FALSE_POSITIVE_RE = re.compile("|".join(_FALSE_POSITIVE_PATTERNS))

MAX_INFER_LENGTH = 300


def _is_false_positive(text: str) -> bool:
    if len(text) > MAX_INFER_LENGTH:
        return True
    return bool(_FALSE_POSITIVE_RE.search(text))


def classify_message(text: str) -> SignalResult | None:
    """Classify a user message for disagreement signals.

    Returns a SignalResult if a signal is detected with confidence >= 0.6,
    or None if no disagreement is found.

    Confidence levels:
    - 1.0: exact match on a fail pattern
    - 0.8: exact match on a partial pattern
    - 0.6: pattern found within a longer message (substring match)
    """
    if not text or not text.strip():
        return None

    if _is_false_positive(text):
        return None

    lowered = text.strip().lower()

    # --- Fail checks (all tiers) before any partial checks ---

    # Exact fail matches (confidence 1.0)
    for pattern in _FAIL_EXACT:
        if lowered == pattern or lowered.startswith(pattern):
            return SignalResult("fail", 1.0, pattern)

    # Prefix fail matches (confidence 1.0)
    for pattern in _FAIL_PREFIX:
        if lowered.startswith(pattern):
            return SignalResult("fail", 1.0, pattern)

    # Substring fail matches (confidence 0.6)
    for pattern in _FAIL_EXACT:
        if pattern in lowered:
            return SignalResult("fail", 0.6, pattern)

    # --- Partial checks only if no fail signal found ---

    # Exact partial matches (confidence 0.8)
    for pattern in _PARTIAL_EXACT:
        if lowered == pattern or lowered.startswith(pattern):
            return SignalResult("partial", 0.8, pattern)

    # Prefix partial matches (confidence 0.8)
    for pattern in _PARTIAL_PREFIX:
        if lowered.startswith(pattern):
            return SignalResult("partial", 0.8, pattern)

    # Substring partial matches (confidence 0.6)
    for pattern in _PARTIAL_EXACT:
        if pattern in lowered:
            return SignalResult("partial", 0.6, pattern)

    return None


def format_inferred_note(result: SignalResult, original: str) -> str:
    """Format the feedback note for an inferred signal."""
    short = original[:100] + "…" if len(original) > 100 else original
    return f'inferred (confidence: {result.confidence:.1f}) — "{short}"'
