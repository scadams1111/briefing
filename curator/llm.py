"""Thin wrapper around the Gemini free tier. Everything works without it,
just with plainer rankings and summaries.

Model names change often and individual models get overloaded, so on start-up
we ask Google which models this key can use, and on an overload we rotate to
the next model instead of hammering the same one."""
from __future__ import annotations

import json
import logging
import os
import re
import time

log = logging.getLogger("curator")
SKIP = re.compile(r"image|tts|audio|live|embed|vision|thinking-exp|learnlm|gemma|computer|robotics|veo|imagen", re.I)


def _version(name: str) -> float:
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


class LLM:
    def __init__(self, cfg: dict):
        c = cfg.get("llm", {})
        self.preferred = list(c.get("models", []))
        self.gap = float(c.get("seconds_between_calls", 5))
        self.deadline = time.time() + 60 * float(c.get("budget_minutes", 12))
        self.failures = 0
        self.key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.client = None
        self.models: list[str] = []
        self._last = 0.0
        if not self.key:
            log.warning("No GEMINI_API_KEY set: using simple ranking and extractive summaries.")
            return
        from google import genai
        self.client = genai.Client(api_key=self.key)
        self.models = self._discover()
        log.info("LLM models in rotation: %s", ", ".join(self.models) or "none")

    def _discover(self) -> list[str]:
        """Preferred models that exist, then other Flash models, newest first, non-lite before lite."""
        try:
            avail = []
            for m in self.client.models.list():
                name = m.name.removeprefix("models/")
                actions = getattr(m, "supported_actions", None) or []
                if "generateContent" in actions and "flash" in name and not SKIP.search(name):
                    avail.append(name)
        except Exception as ex:
            log.warning("couldn't list models (%s); using config list", ex)
            return self.preferred
        ordered = [m for m in self.preferred if m in avail]
        rest = sorted((m for m in avail if m not in ordered),
                      key=lambda n: ("preview" in n or "exp" in n, "lite" in n, -_version(n), n))
        return (ordered + rest)[:6]

    @property
    def available(self) -> bool:
        return (self.client is not None and bool(self.models)
                and self.failures < 3 and time.time() < self.deadline)

    def json(self, prompt: str) -> dict | None:
        if not self.available:
            return None
        from google.genai import errors, types
        conf = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3)
        tries = 0
        max_tries = len(self.models) + 1
        while tries < max_tries and self.models and time.time() < self.deadline:
            wait = self.gap - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            model = self.models[0]
            tries += 1
            try:
                resp = self.client.models.generate_content(model=model, contents=prompt, config=conf)
                self.failures = 0
                return _loads(resp.text)
            except errors.ClientError as ex:
                code = getattr(ex, "code", None)
                if code in (400, 403, 404):          # model gone or not allowed on this key
                    log.warning("model %s unusable (%s); dropping it", model, code)
                    self.models.pop(0)
                    continue
                if code == 429:                      # this model's free quota is used up: rotate
                    log.warning("model %s rate-limited; rotating", model)
                    self._rotate()
                    time.sleep(5)
                    continue
                log.error("LLM client error: %s", ex)
                return None
            except errors.ServerError as ex:        # overloaded / temporary: try another model
                log.warning("model %s busy (%s); rotating", model, getattr(ex, "code", ""))
                self._rotate()
                time.sleep(3)
            except Exception as ex:
                log.warning("LLM error on %s (%s)", model, ex)
                self._rotate()
                time.sleep(5)
        self.failures += 1
        log.error("LLM gave up on this item; using fallback")
        if not self.available:
            log.error("Gemini looks unavailable right now; finishing without it (a catch-up run will retry)")
        return None

    def _rotate(self) -> None:
        if len(self.models) > 1:
            self.models.append(self.models.pop(0))


def _loads(text: str) -> dict | None:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else None
