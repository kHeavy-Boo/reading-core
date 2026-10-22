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
from typing import Any

VOICEVOX_URL = "http://127.0.0.1:50021"
TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class ReadingCorrection:
    word: str                  # Original kanji word, e.g. "人気"
    reading: str               # Context-selected reading, e.g. "ひとけ"


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

    def synthesize(self, query: dict, speaker: int) -> bytes:
        return _post_json(
            f"{self.voicevox_url}/synthesis",
            params={"speaker": speaker},
            payload=query,
        )
