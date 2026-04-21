#!/usr/bin/env python3
"""
OpenRouter Vision Model Compatibility Probe
============================================
Fetches every vision-capable model from the OpenRouter catalogue and tests whether
each one can:

  1. CLUE  — given a card image, return a short non-empty clue (creative style)
  2. VOTE  — given the same image + that clue, return a parseable 0-10 score

A model is marked PASS/FAIL per test.  Results are printed as a table and saved
to tests/openrouter_model_results.json for later use (e.g. to build an allowlist).

Usage (from project root):
    python tests/test_openrouter_compatibility.py

Options (environment variables):
    CONCURRENCY=8          how many models to probe in parallel (default 8)
    TEST_IMAGE=data/1_full/1.jpg   card image to use (default data/1_full/1.jpg)
    TIMEOUT=30             per-request timeout in seconds (default 30)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap: ensure src/ is on the path so we can import prompts
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

load_dotenv(ROOT / ".env")

from core.prompts import PROMPT_STYLES  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
CONCURRENCY = int(os.getenv("CONCURRENCY", "8"))
TIMEOUT = float(os.getenv("TIMEOUT", "30"))
TEST_IMAGE_PATH = os.getenv("TEST_IMAGE", str(ROOT / "data/1_full/1.jpg"))
RESULTS_PATH = ROOT / "tests" / "openrouter_model_results.json"
COMPATIBLE_MODELS_PATH = ROOT / "data" / "compatible_models.json"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# Use the creative style prompts — most likely to succeed across models
_STYLE = PROMPT_STYLES["creative"]
CLUE_PROMPT = _STYLE.clue_prompt
VOTE_PROMPT_TEMPLATE = _STYLE.vote_prompt  # needs .format(clue=...)
CLUE_MAX_TOKENS = _STYLE.max_tokens
VOTE_MAX_TOKENS = 16  # some models (e.g. gpt-5.4) require >= 16
TEMPERATURE = _STYLE.temperature

# Phrases that indicate a model returned a refusal rather than actual content
_REFUSAL_PHRASES = (
    "i cannot", "i can't", "i'm unable", "i am unable",
    "no image", "no story", "no clue", "not provided",
    "cannot provide", "unable to provide",
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("compat_probe")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class ModelResult:
    model_id: str
    model_name: str

    # Clue test
    clue_ok: bool = False
    clue_response: str = ""
    clue_latency_s: float = 0.0
    clue_error: str = ""

    # Vote test
    vote_ok: bool = False
    vote_response: str = ""
    vote_score: float | None = None
    vote_latency_s: float = 0.0
    vote_error: str = ""

    @property
    def compatible(self) -> bool:
        return self.clue_ok and self.vote_ok

    @property
    def status(self) -> str:
        if self.compatible:
            return "PASS"
        parts = []
        if not self.clue_ok:
            parts.append("clue")
        if not self.vote_ok:
            parts.append("vote")
        return "FAIL(" + "+".join(parts) + ")"


# ---------------------------------------------------------------------------
# OpenRouter helpers
# ---------------------------------------------------------------------------
def _encode_image(path: str) -> tuple[str, str]:
    """Return (base64_data, media_type)."""
    ext = path.lower().rsplit(".", 1)[-1]
    media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode(), media_type


def _is_refusal(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in _REFUSAL_PHRASES)


def _parse_score(raw: str) -> float | None:
    try:
        first = raw.strip().split()[0].rstrip(".,/").split("/")[0]
        val = float(first)
        if 0.0 <= val <= 10.0:
            return val
        return None
    except (ValueError, IndexError):
        return None


async def _call(
    client: httpx.AsyncClient,
    model_id: str,
    image_b64: str,
    media_type: str,
    prompt: str,
    max_tokens: int,
) -> tuple[str, str]:
    """Return (response_text, error_string).  error_string is '' on success."""
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": TEMPERATURE,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                ],
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/LLM_dixit",
        "X-Title": "LLM Dixit Compat Probe",
    }
    try:
        resp = await client.post(OPENROUTER_CHAT_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            body = resp.text[:300]
            return "", f"HTTP {resp.status_code}: {body}"
        data = resp.json()
        if "error" in data:
            return "", f"API error: {str(data['error'])[:200]}"
        content = data["choices"][0]["message"]["content"] or ""
        return content, ""
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"


async def fetch_all_models() -> list[dict]:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(OPENROUTER_MODELS_URL, headers=headers)
        resp.raise_for_status()
        return resp.json().get("data", [])


# ---------------------------------------------------------------------------
# Single-model probe
# ---------------------------------------------------------------------------
async def probe_model(
    model: dict,
    image_b64: str,
    media_type: str,
    semaphore: asyncio.Semaphore,
    progress: list[int],
    total: int,
) -> ModelResult:
    model_id = model["id"]
    model_name = model.get("name", model_id)
    result = ModelResult(model_id=model_id, model_name=model_name)

    async with semaphore:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # --- Clue test ---
            t0 = time.perf_counter()
            clue_text, clue_err = await _call(
                client, model_id, image_b64, media_type, CLUE_PROMPT, CLUE_MAX_TOKENS
            )
            result.clue_latency_s = round(time.perf_counter() - t0, 2)
            result.clue_response = clue_text[:200]
            result.clue_error = clue_err

            if clue_err:
                result.clue_ok = False
            elif not clue_text.strip():
                result.clue_ok = False
                result.clue_error = "empty response"
            elif _is_refusal(clue_text):
                result.clue_ok = False
                result.clue_error = "refusal"
            else:
                result.clue_ok = True

            # --- Vote test ---
            # Use the generated clue if available, else a safe fallback
            test_clue = clue_text.strip() if result.clue_ok else "a dream of flying"
            vote_prompt = VOTE_PROMPT_TEMPLATE.format(clue=test_clue)

            t0 = time.perf_counter()
            vote_text, vote_err = await _call(
                client, model_id, image_b64, media_type, vote_prompt, VOTE_MAX_TOKENS
            )
            result.vote_latency_s = round(time.perf_counter() - t0, 2)
            result.vote_response = vote_text[:200]
            result.vote_error = vote_err

            if vote_err:
                result.vote_ok = False
            elif not vote_text.strip():
                result.vote_ok = False
                result.vote_error = "empty response"
            else:
                score = _parse_score(vote_text)
                if score is not None:
                    result.vote_ok = True
                    result.vote_score = score
                else:
                    result.vote_ok = False
                    result.vote_error = f"unparseable: {vote_text[:80]}"

    progress[0] += 1
    symbol = "✓" if result.compatible else "✗"
    print(f"  [{progress[0]:3d}/{total}] {symbol} {model_id:<55} clue={result.clue_ok!s:<5} vote={result.vote_ok!s:<5} ({result.clue_latency_s+result.vote_latency_s:.1f}s)")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    if not API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    if not Path(TEST_IMAGE_PATH).exists():
        print(f"ERROR: test image not found: {TEST_IMAGE_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*70}")
    print("  OpenRouter Vision Model Compatibility Probe")
    print(f"  Image : {TEST_IMAGE_PATH}")
    print(f"  Style : creative (clue_prompt + vote_prompt)")
    print(f"  Concurrency: {CONCURRENCY}  |  Timeout: {TIMEOUT}s")
    print(f"{'='*70}\n")

    # Fetch model catalogue
    print("Fetching full model catalogue from OpenRouter…")
    models = await fetch_all_models()
    models.sort(key=lambda m: m["id"])
    print(f"Found {len(models)} models total (no pre-filtering).\n")

    image_b64, media_type = _encode_image(TEST_IMAGE_PATH)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    progress = [0]

    tasks = [
        probe_model(m, image_b64, media_type, semaphore, progress, len(models))
        for m in models
    ]
    results: list[ModelResult] = await asyncio.gather(*tasks)
    results.sort(key=lambda r: (not r.compatible, r.model_id))

    # ---------------------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------------------
    passing = [r for r in results if r.compatible]
    failing = [r for r in results if not r.compatible]

    print(f"\n{'='*70}")
    print(f"  RESULTS  —  {len(passing)} pass / {len(failing)} fail / {len(results)} total")
    print(f"{'='*70}")

    col_w = 55
    print(f"\n{'PASS':^6}  {'MODEL':<{col_w}}  {'CLUE_MS':>8}  {'VOTE_MS':>8}  {'SCORE':>6}")
    print("-" * (col_w + 38))
    for r in results:
        mark = "PASS" if r.compatible else "FAIL"
        score_str = f"{r.vote_score:.1f}" if r.vote_score is not None else "—"
        print(
            f"{mark:^6}  {r.model_id:<{col_w}}  "
            f"{r.clue_latency_s*1000:>7.0f}ms  "
            f"{r.vote_latency_s*1000:>7.0f}ms  "
            f"{score_str:>6}"
        )
        if not r.compatible:
            if r.clue_error:
                print(f"{'':8}  clue error : {r.clue_error}")
            if r.vote_error:
                print(f"{'':8}  vote error : {r.vote_error}")

    # ---------------------------------------------------------------------------
    # Compatible model list (copy-paste ready)
    # ---------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print(f"  {len(passing)} compatible models:")
    print(f"{'='*70}")
    for r in passing:
        print(f"    {r.model_id}")

    # ---------------------------------------------------------------------------
    # Save full results JSON
    # ---------------------------------------------------------------------------
    output = {
        "run_at": datetime.now().isoformat(),
        "test_image": TEST_IMAGE_PATH,
        "total": len(results),
        "passing": len(passing),
        "failing": len(failing),
        "results": [asdict(r) for r in results],
    }
    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nFull results saved to: {RESULTS_PATH}")

    # ---------------------------------------------------------------------------
    # Save compatible_models.json — consumed by GET /api/models
    # ---------------------------------------------------------------------------
    compatible = {
        "updated_at": datetime.now().isoformat(),
        "models": [{"id": r.model_id, "name": r.model_name} for r in passing],
    }
    COMPATIBLE_MODELS_PATH.parent.mkdir(exist_ok=True)
    COMPATIBLE_MODELS_PATH.write_text(json.dumps(compatible, indent=2))
    print(f"Compatible model list saved to: {COMPATIBLE_MODELS_PATH}\n")


if __name__ == "__main__":
    asyncio.run(main())
