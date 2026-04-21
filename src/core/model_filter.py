"""
OpenRouter model catalogue filter.

Shared between the API route (GET /api/models) and the compatibility probe script.
"""

from __future__ import annotations

# Keywords searched in model description / name when modality metadata is absent
_VISION_KEYWORDS = (
    "vision", "visual", "image", "multimodal", "multi-modal",
    "vl", "vlm", "ocr", "screenshot", "pixel",
)


def is_vision_chat(m: dict) -> bool:
    """Return True if the OpenRouter model object supports image input → text output.

    Resolution order:
    1. Structured modality metadata (``architecture.input_modalities`` /
       ``architecture.modality``) — authoritative when present.
    2. Model description / name keyword scan — catches models like
       ``openai/gpt-5`` where OpenRouter hasn't yet populated the modality
       fields but the description explicitly mentions vision capability.
    """
    arch = m.get("architecture", {})
    inputs = arch.get("input_modalities", [])
    outputs = arch.get("output_modalities", [])
    modality = arch.get("modality", "")

    # --- 1. Structured metadata ---
    if inputs or modality:
        has_image_in = "image" in inputs or (
            "image" in modality
            and "->" in modality
            and modality.index("image") < modality.index("->")
        )
        outputs_text = (not outputs) or "text" in outputs
        if has_image_in and outputs_text:
            return True
        # If metadata is present but says no image input, trust it
        # (don't fall through to keyword scan — we don't want false positives)
        if inputs or modality:
            return False

    # --- 2. Keyword scan (metadata absent or empty) ---
    haystack = " ".join([
        m.get("name", ""),
        m.get("description", ""),
        m.get("id", ""),
    ]).lower()
    return any(kw in haystack for kw in _VISION_KEYWORDS)
