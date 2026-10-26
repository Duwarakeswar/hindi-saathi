"""Thin client for the Sarvam AI REST APIs used by Hindi Saathi.

Docs: https://docs.sarvam.ai/api-reference/introduction
"""

from __future__ import annotations

import base64
import os

import requests

API_BASE = os.getenv("SARVAM_API_BASE", "https://api.sarvam.ai")
CHAT_MODEL = os.getenv("SARVAM_CHAT_MODEL", "sarvam-105b")
REASONING_EFFORT = os.getenv("SARVAM_REASONING_EFFORT", "low")
TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
TTS_SPEAKER = os.getenv("SARVAM_TTS_SPEAKER", "priya")
STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v4")


class SarvamError(Exception):
    pass


def get_api_key() -> str:
    key = os.getenv("SARVAM_API_KEY", "")
    if not key:
        try:  # Streamlit Community Cloud secrets
            import streamlit as st

            key = st.secrets.get("SARVAM_API_KEY", "")
        except Exception:
            pass
    return key


class SarvamClient:
    def __init__(self, api_key: str | None = None, timeout: int = 90):
        self.api_key = api_key or get_api_key()
        if not self.api_key:
            raise SarvamError("Missing SARVAM_API_KEY. Add it to .env or Streamlit secrets.")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["api-subscription-key"] = self.api_key

    def _post(self, path: str, **kwargs) -> dict:
        try:
            resp = self.session.post(f"{API_BASE}{path}", timeout=self.timeout, **kwargs)
        except requests.RequestException as err:
            raise SarvamError(f"Could not reach Sarvam API: {err}") from err
        if resp.status_code != 200:
            try:
                detail = resp.json().get("error", {}).get("message") or resp.text
            except ValueError:
                detail = resp.text
            if resp.status_code == 403:
                detail = "Invalid Sarvam API key."
            elif resp.status_code == 429:
                detail = "Rate limit reached - wait a few seconds and try again."
            raise SarvamError(f"Sarvam {path} failed ({resp.status_code}): {detail}")
        return resp.json()

    # ---- LLM -----------------------------------------------------------------

    def chat(
        self, messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 4096, json_mode: bool = False
    ) -> dict:
        """Chat completion with optional tool calling or JSON output. Returns the first choice."""
        body = {"model": CHAT_MODEL, "messages": messages, "max_tokens": max_tokens, "reasoning_effort": REASONING_EFFORT}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        return self._post("/v1/chat/completions", json=body)["choices"][0]

    # ---- text ----------------------------------------------------------------

    def translate(
        self,
        text: str,
        source: str = "auto",
        target: str = "hi-IN",
        mode: str = "formal",
        speaker_gender: str | None = None,
    ) -> dict:
        """Mayura translation. Returns {translated_text, source_language_code}."""
        body = {
            "input": text[:1000],
            "source_language_code": source,
            "target_language_code": target,
            "model": "mayura:v1",
            "mode": mode,
        }
        if speaker_gender:
            body["speaker_gender"] = speaker_gender
        if target == "hi-IN":
            # Colloquial mode keeps English loanwords in Latin script; learners need them in Devanagari.
            body["output_script"] = "fully-native"
        return self._post("/translate", json=body)

    def romanize(self, hindi: str) -> str:
        """Devanagari -> Roman script so learners can read the pronunciation."""
        body = {"input": hindi[:1000], "source_language_code": "hi-IN", "target_language_code": "en-IN"}
        return self._post("/transliterate", json=body)["transliterated_text"]

    # ---- speech --------------------------------------------------------------

    def speak(self, text: str, pace: float = 0.9, speaker: str = TTS_SPEAKER) -> bytes:
        """Bulbul text-to-speech in Hindi. Returns WAV bytes."""
        body = {
            "text": text[:2500],
            "language_code": "hi-IN",
            "model": TTS_MODEL,
            "speaker": speaker,
            "pace": pace,
        }
        audios = self._post("/text-to-speech", json=body)["audios"]
        return base64.b64decode("".join(audios))

    def transcribe(self, audio: bytes, filename: str = "speech.wav", language: str = "hi-IN") -> dict:
        """Saaras speech-to-text. Returns {transcript, language_code}."""
        files = {"file": (filename, audio, "audio/wav")}
        data = {"model": STT_MODEL, "language_code": language}
        return self._post("/speech-to-text", files=files, data=data)
