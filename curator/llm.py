"""Thin wrapper around the Gemini free tier. Everything works without it,
just with plainer rankings and summaries."""
from __future__ import annotations

import json
import logging
import os
import re
import time

log = logging.getLogger("curator")


class LLM:
    def __init__(self, cfg: dict):
        c = cfg.get("llm", {})
        self.models = list(c.get("models", []))
        self.gap = float(c.get("seconds_between_calls", 5))
        self.key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.client = None
        self._last = 0.0
        if self.key:
            from google import genai
            self.client = genai.Client(api_key=self.key)
        else:
            log.warning("No GEMINI_API_KEY set: using simple ranking and extractive summaries.")

    @property
    def available(self) -> bool:
        return self.client is not None and bool(self.models)

    def json(self, prompt: str, retries: int = 4) -> dict | None:
        if not self.available:
            return None
        from google.genai import types, errors
        conf = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3)
        attempt = 0
        while attempt < retries and self.models:
            wait = self.gap - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            model = self.models[0]
            try:
                resp = self.client.models.generate_content(model=model, contents=prompt, config=conf)
                return _loads(resp.text)
            except errors.ClientError as ex:
                code = getattr(ex, "code", None)
                if code == 404 or "not found" in str(ex).lower():
                    log.warning("model %s unavailable, trying next", model)
                    self.models.pop(0)
                    continue
                if code == 429:
                    attempt += 1
                    log.warning("rate limited, backing off")
                    time.sleep(30 * attempt)
                    continue
                log.error("LLM client error: %s", ex)
                return None
            except Exception as ex:
                attempt += 1
                log.warning("LLM error (%s), retrying", ex)
                time.sleep(10 * attempt)
        log.error("LLM gave up; falling back")
        return None


def _loads(text: str) -> dict | None:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else None
