"""Skully Reading Engine — Stage 1: VOICEVOX synthesis-path experiment.

This module does not edit ChatGPT's displayed text, Ver.6.1, or VOICEVOX's
standard dictionary.  Stage 1 verifies that a pronunciation selected later
by a context-aware AI can reach VOICEVOX without breaking accent/mora JSON.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VOICEVOX_URL = "http://127.0.0.1:50021"
TIMEOUT_SECONDS = 15
READING_MD = Path(__file__).with_name("MISREAD_WORDS.md")
ACTIVE_HEADER = "## 再生に適用する登録語"


@dataclass(frozen=True)
class ReadingCorrection:
    word: str                  # Original kanji word, e.g. "人気"
    reading: str               # Context-selected reading, e.g. "ひとけ"



def _check_reading(correction: ReadingCorrection) -> None:
    if not correction.word or not correction.reading:
        raise ValueError("word and reading cannot be blank")
    if not all("ぁ" <= ch <= "ゖ" or ch == "ー" for ch in correction.reading):
        raise ValueError("reading must contain only hiragana and prolonged vowel marks")


def _is_kanji(char: str) -> bool:
    return "\u3400" <= char <= "\u9fff" or char == "々"


def _single_safe_span(text: str, word: str) -> tuple[int, int] | None:
    """Reject repeated occurrences and embedded kanji compounds (conservative)."""
    if text.count(word) != 1:
        return None
    start = text.find(word)
    end = start + len(word)
    if _is_kanji(word[0]) and start and _is_kanji(text[start - 1]):
        return None
    if _is_kanji(word[-1]) and end < len(text) and _is_kanji(text[end]):
        return None
    return start, end


def registered_readings(text: str, md_path: str | Path = READING_MD) -> list[ReadingCorrection]:
    """Read only the registered table, using literal context substring matching.

    Specific context rules take precedence over '*' for the same word.
    """
    path = Path(md_path)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    active = False
    rules: list[tuple[str, str, str]] = []
    for line in lines:
        stripped = line.strip()
        if stripped == ACTIVE_HEADER:
            active = True
            continue
        if active and stripped.startswith("## "):
            break
        if not active or not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0] in ("表記", "---") or set(cells[0]) == {"-"}:
            continue
        if len(cells) != 4:
            raise ValueError(f"invalid misread table row: {stripped}")
        word, reading, condition, _note = cells
        if not word or not condition or not reading or condition == "適用条件":
            raise ValueError(f"incomplete misread rule: {stripped}")
        _check_reading(ReadingCorrection(word, reading))
        rules.append((word, reading, condition))

    chosen: dict[str, tuple[str, str, int]] = {}
    for word, reading, condition in rules:
        if word not in text or (condition != "*" and condition not in text):
            continue
        if _single_safe_span(text, word) is None:
            continue
        priority = 0 if condition == "*" else len(condition)
        if word in chosen and chosen[word][2] > priority:
            continue
        if word in chosen and chosen[word][2] == priority and chosen[word][0] != reading:
            raise ValueError(f"conflicting misread rules for {word}")
        chosen[word] = (reading, condition, priority)

    selected: list[tuple[int, int, ReadingCorrection]] = []
    for word in sorted(chosen, key=lambda w: (-len(w), w)):
        span = _single_safe_span(text, word)
        if span is None:
            continue
        start, end = span
        if any(start < other_end and other_start < end for other_start, other_end, _ in selected):
            continue
        selected.append((start, end, ReadingCorrection(word, chosen[word][0])))
    selected.sort(key=lambda item: item[0])
    return [correction for _, _, correction in selected]


def _post_json(url: str, *, params: dict[str, Any], payload: dict | None = None) -> Any:
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    data = b"" if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(full_url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
        if payload is None:
            return json.load(response)
        return response.read()


class ReadingEngine:
    def __init__(self, voicevox_url: str = VOICEVOX_URL):
        self.voicevox_url = voicevox_url.rstrip("/")

    def audio_query(self, text: str, speaker: int, speed: float = 1.0) -> dict:
        query = _post_json(
            f"{self.voicevox_url}/audio_query",
            params={"text": text, "speaker": speaker},
        )
        query["speedScale"] = float(speed)
        return query

    def corrected_query(
        self,
        original_text: str,
        correction: ReadingCorrection,
        speaker: int,
        speed: float = 1.0,
    ) -> tuple[str, dict]:
        """Create a *new* consistent audio_query for TTS only.

        We intentionally do not mutate accent_phrases.moras manually: rebuilding
        the whole VOICEVOX query keeps mora, accent, and phoneme fields aligned.
        Context analysis and trust policy are out of scope for Stage 1.
        """
        if not correction.word or not correction.reading:
            raise ValueError("word and reading cannot be blank")
        if original_text.count(correction.word) != 1:
            raise ValueError("target word must appear exactly once in the sentence")
        if not all("ぁ" <= ch <= "ゖ" or ch == "ー" for ch in correction.reading):
            raise ValueError("reading must contain only hiragana and prolonged vowel marks")

        tts_only_text = original_text.replace(correction.word, correction.reading, 1)
        query = self.audio_query(tts_only_text, speaker=speaker, speed=speed)
        return tts_only_text, query

    def corrected_query_many(
        self,
        original_text: str,
        corrections: list[ReadingCorrection],
        speaker: int,
        speed: float = 1.0,
    ) -> tuple[str, dict]:
        """Apply multiple nonoverlapping readings, then regenerate audio_query once."""
        if not corrections:
            raise ValueError("corrections cannot be empty")
        spans = []
        for correction in corrections:
            _check_reading(correction)
            if original_text.count(correction.word) != 1:
                raise ValueError("each corrected word must appear exactly once")
            start = original_text.index(correction.word)
            end = start + len(correction.word)
            if any(start < other_end and other_start < end for other_start, other_end, _ in spans):
                raise ValueError("overlapping reading corrections")
            spans.append((start, end, correction))
        spoken = original_text
        for start, end, correction in sorted(spans, reverse=True):
            spoken = spoken[:start] + correction.reading + spoken[end:]
        return spoken, self.audio_query(spoken, speaker=speaker, speed=speed)

    def synthesize(self, query: dict, speaker: int) -> bytes:
        return _post_json(
            f"{self.voicevox_url}/synthesis",
            params={"speaker": speaker},
            payload=query,
        )
