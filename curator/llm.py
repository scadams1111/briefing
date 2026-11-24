"""AI backends: Gemini first, Groq as backup. Both are free tiers.
Everything still works with neither, just with plainer rankings and summaries.

Model names change often and individual models get overloaded, so each backend
asks its provider which models this key can use, rotates to another model when
one is busy, and switches itself off for the rest of the run after repeated
failures so the run always finishes on time."""
from __future__ import annotations

import json
import logging
import os
import re
import time

import requests

log = logging.getLogger("curator")


def _version(name: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


class Backend:
    name = "backend"

    def __init__(self, gap: float):
        self.gap = gap
        self.models: list[str] = []
        self.failures = 0
        self._last = 0.0

    @property
    def available(self) -> bool:
        return bool(self.models) and self.failures < 3

    def _pace(self):
        wait = self.gap - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def _rotate(self):
        if len(self.models) > 1:
            self.models.append(self.models.pop(0))

    def json(self, prompt: str, deadline: float) -> dict | None:
        tries, max_tries = 0, len(self.models) + 1
        while tries < max_tries and self.models and time.time() < deadline:
            self._pace()
            tries += 1
            model = self.models[0]
            kind, out = self._call(model, prompt)
            if kind == "ok":
                parsed = _loads(out)
                if parsed is not None:
                    self.failures = 0
                    return parsed
                log.warning("%s model %s returned unreadable JSON", self.name, model)
                self._rotate()
            elif kind == "gone":
                log.warning("%s model %s unusable; dropping it", self.name, model)
                self.models.pop(0)
            elif kind in ("busy", "limited"):
                log.warning("%s model %s %s; rotating", self.name, model, kind)
                self._rotate()
                time.sleep(3 if kind == "busy" else 5)
            else:
                log.warning("%s error on %s: %s", self.name, model, out[:200])
                self._rotate()
                time.sleep(5)
        self.failures += 1
        if not self.available:
            log.error("%s looks unavailable right now; not using it for the rest of this run", self.name)
        return None

    def _call(self, model: str, prompt: str) -> tuple[str, str]:
        raise NotImplementedError


class Gemini(Backend):
    name = "Gemini"
    SKIP = re.compile(r"image|tts|audio|live|embed|vision|thinking-exp|learnlm|gemma|computer|robotics|veo|imagen", re.I)

    def __init__(self, key: str, preferred: list[str], gap: float):
        super().__init__(gap)
        from google import genai
        self.client = genai.Client(api_key=key)
        try:
            avail = [m.name.removeprefix("models/") for m in self.client.models.list()
                     if "generateContent" in (getattr(m, "supported_actions", None) or [])
                     and "flash" in m.name and not self.SKIP.search(m.name)]
            ordered = [m for m in preferred if m in avail]
            rest = sorted((m for m in avail if m not in ordered),
                          key=lambda n: ("preview" in n or "exp" in n, "lite" in n, -_version(n), n))
            self.models = (ordered + rest)[:6]
        except Exception as ex:
            log.warning("couldn't list Gemini models (%s); using config list", ex)
            self.models = list(preferred)

    def _call(self, model, prompt):
        from google.genai import errors, types
        conf = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3)
        try:
            return "ok", self.client.models.generate_content(model=model, contents=prompt, config=conf).text
        except errors.ClientError as ex:
            code = getattr(ex, "code", None)
            if code in (400, 403, 404):
                return "gone", str(ex)
            if code == 429:
                return "limited", str(ex)
            return "error", str(ex)
        except errors.ServerError as ex:
            return "busy", str(ex)
        except Exception as ex:
            return "error", str(ex)


class Groq(Backend):
    name = "Groq"
    URL = "https://api.groq.com/openai/v1"
    SKIP = re.compile(r"whisper|tts|guard|embed|vision|playai|distil|compound|orpheus|prompt", re.I)

    def __init__(self, key: str, preferred: list[str], gap: float):
        super().__init__(gap)
        self.h = {"Authorization": f"Bearer {key}"}
        try:
            r = requests.get(f"{self.URL}/models", headers=self.h, timeout=20)
            r.raise_for_status()
            avail = [m["id"] for m in r.json().get("data", [])
                     if m.get("active", True) and not self.SKIP.search(m["id"])]
            ordered = [m for m in preferred if m in avail]

            def size(n):  # prefer bigger models (120b, 70b, ...)
                m = re.search(r"(\d+)b\b", n)
                return -float(m.group(1)) if m else 0.0
            rest = sorted((m for m in avail if m not in ordered), key=lambda n: (size(n), n))
            self.models = (ordered + rest)[:5]
        except Exception as ex:
            log.warning("couldn't list Groq models (%s); using config list", ex)
            self.models = list(preferred)

    def _call(self, model, prompt):
        try:
            r = requests.post(f"{self.URL}/chat/completions", headers=self.h, timeout=90, json={
                "model": model, "temperature": 0.3,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}]})
        except Exception as ex:
            return "error", str(ex)
        if r.status_code == 200:
            return "ok", r.json()["choices"][0]["message"].get("content") or ""
        if r.status_code in (401, 403, 404):
            return "gone", r.text[:200]
        if r.status_code in (413, 429):
            return "limited", r.text[:200]
        if r.status_code >= 500:
            return "busy", r.text[:200]
        return "error", f"{r.status_code} {r.text[:200]}"


class LLM:
    """Tries each available backend in order for every request."""

    def __init__(self, cfg: dict):
        c = cfg.get("llm", {})
        gap = float(c.get("seconds_between_calls", 5))
        self.deadline = time.time() + 60 * float(c.get("budget_minutes", 12))
        self.backends: list[Backend] = []
        if k := os.environ.get("GEMINI_API_KEY", "").strip():
            self.backends.append(Gemini(k, list(c.get("models", [])), gap))
        if k := os.environ.get("GROQ_API_KEY", "").strip():
            self.backends.append(Groq(k, list(c.get("groq_models", [])),
                                      float(c.get("groq_seconds_between_calls", 3))))
        for b in self.backends:
            log.info("%s models in rotation: %s", b.name, ", ".join(b.models) or "none")
        if not self.backends:
            log.warning("No AI keys set: using simple ranking and extractive summaries.")

    @property
    def available(self) -> bool:
        return time.time() < self.deadline and any(b.available for b in self.backends)

    def json(self, prompt: str) -> dict | None:
        for b in self.backends:
            if b.available and time.time() < self.deadline:
                out = b.json(prompt, self.deadline)
                if out is not None:
                    return out
        log.error("no AI backend answered; using fallback for this item")
        return None


def _loads(text: str) -> dict | None:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        try:
            return json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            return None
