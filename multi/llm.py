"""Thin OpenRouter client (stdlib only) for the real-LLM backend.

Reads the API key + model the same way the repo's mini-coding-agent does:
  - env var OPENROUTER_API_KEY / MODEL first
  - else parse ../OPENROUTER.txt
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def _key_file() -> Path:
    return Path(__file__).resolve().parent.parent / "OPENROUTER.txt"


def api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    f = _key_file()
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    return ""


def model() -> str:
    m = os.environ.get("MODEL")
    if m:
        return m
    f = _key_file()
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith("MODEL="):
                return line.split("=", 1)[1].strip().strip('"')
    return "deepseek/deepseek-v4.1-flash"


def _available() -> bool:
    return bool(api_key())


def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    if not _available():
        raise RuntimeError(
            "No OPENROUTER_API_KEY. Set the env var or add ../OPENROUTER.txt "
            "to use the real-LLM mode; or use scripted mode (no key needed).")
    body = {"model": model(), "messages": messages}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + api_key(),
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())
