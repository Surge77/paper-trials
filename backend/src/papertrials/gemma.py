"""Gemma, running locally through Ollama.

Three small jobs, each with a plain fallback so the app still works when
Ollama isn't running:

1. Read the note you typed after a flight ("stalled then dropped, veered
   left") and turn it into issue tags the recommender can act on.
2. Write a two-sentence lab note after each experiment from numbers the
   code has already worked out. Any number Gemma writes that isn't in those
   facts gets the note rejected, so it can't invent results.
3. Look at an optional photo of the plane and estimate symmetry and nose
   shape. This is shown as an estimate and never fed to the model.
"""

import asyncio
import base64
import json
import logging
import re
from typing import Any

import httpx

from papertrials.config import get_settings

log = logging.getLogger(__name__)

# Notes are parsed while you wait for the save, so a slow model falls back to keywords quickly.
NOTE_TIMEOUT_S = 15.0

ISSUES = ("stall", "nose_dive", "spiral", "veer_left", "veer_right", "flutter", "tumble")

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "stall": ("stall", "stalled", "climbed then dropped", "nose up", "swoop"),
    "nose_dive": ("nose dive", "nosedive", "dived", "dove", "crashed straight", "nose down", "dropped like"),
    "spiral": ("spiral", "spun", "corkscrew", "circled"),
    "veer_left": ("veered left", "went left", "pulled left", "banked left", "curved left", "drifted left"),
    "veer_right": ("veered right", "went right", "pulled right", "banked right", "curved right", "drifted right"),
    "flutter": ("flutter", "wobbl", "shook", "shaky"),
    "tumble": ("tumble", "flipped", "somersault", "rolled over"),
}

_NOTE_SCHEMA = {
    "type": "object",
    "properties": {"issues": {"type": "array", "items": {"type": "string", "enum": list(ISSUES)}}},
    "required": ["issues"],
}

_PHOTO_SCHEMA = {
    "type": "object",
    "properties": {
        "symmetry": {"type": "string", "enum": ["even", "uneven", "unclear"]},
        "nose": {"type": "string", "enum": ["sharp", "blunt", "unclear"]},
        "winglets_visible": {"type": "boolean"},
        "comment": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["symmetry", "nose", "winglets_visible", "comment", "confidence"],
}


async def _chat(prompt: str, schema: dict[str, Any] | None = None, image: bytes | None = None) -> str:
    settings = get_settings()
    message: dict[str, Any] = {"role": "user", "content": prompt}
    if image is not None:
        message["images"] = [base64.b64encode(image).decode()]
    body: dict[str, Any] = {
        "model": settings.gemma_model,
        "messages": [message],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if schema is not None:
        body["format"] = schema
    async with httpx.AsyncClient(timeout=settings.gemma_timeout_s) as client:
        response = await client.post(f"{settings.ollama_url}/api/chat", json=body)
        response.raise_for_status()
        return str(response.json()["message"]["content"])


async def is_available() -> bool:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            response.raise_for_status()
            names = {m.get("name") for m in response.json().get("models", [])}
            return settings.gemma_model in names
    except (httpx.HTTPError, ValueError):
        return False


def issues_from_keywords(note: str) -> list[str]:
    text = note.lower()
    return [issue for issue, words in _KEYWORDS.items() if any(w in text for w in words)]


async def parse_note(note: str | None) -> tuple[list[str], str | None]:
    """Returns (issues, source) where source is 'gemma', 'keywords' or None for an empty note."""
    if not note or not note.strip():
        return [], None
    prompt = (
        "You label paper airplane flight notes. Pick every problem the note describes, "
        f"from this list only: {', '.join(ISSUES)}. "
        "stall = climbs then slows and drops; nose_dive = points down and drops fast; "
        "veer_left / veer_right = drifts or curves to that side; "
        "spiral = turns in a tightening circle or spins down; flutter = wobbles or shakes; "
        "tumble = flips over end over end. "
        "If the flight sounds fine, return an empty list.\n\n"
        f"Note: {note.strip()[:500]}"
    )
    try:
        data = json.loads(await asyncio.wait_for(_chat(prompt, _NOTE_SCHEMA), NOTE_TIMEOUT_S))
        issues = [i for i in dict.fromkeys(data.get("issues", [])) if i in ISSUES]
        return issues, "gemma"
    except (httpx.HTTPError, ValueError, KeyError, TypeError, TimeoutError) as exc:
        log.info("Gemma note parsing unavailable, using keywords: %s", exc)
        return issues_from_keywords(note), "keywords"


_NUMBER = re.compile(r"(\d+(?:\.\d+)?)\s*(cm|mm|gsm|m|s|°)?(?![a-zA-Z])")


def render_facts(facts: dict[str, Any]) -> str:
    """The facts as plain lines with units, which is what Gemma sees."""
    lines = [f"Experiment number: {facts['number']}", f"Flights: {facts['flights']}",
             f"Median distance: {facts['median_m']} m"]
    if facts.get("changed"):
        lines.append(f"The one change from the previous plane: {facts['changed']}")
    else:
        lines.append("The one change from the previous plane: none, this is a starting plane")
    if "parent_median_m" in facts:
        lines.append(f"Previous plane's median distance: {facts['parent_median_m']} m")
    if facts.get("predicted_low") is not None:
        where = "inside" if facts.get("inside_prediction") else "outside"
        lines.append(
            f"Predicted range for the median distance, made before flying: "
            f"{facts['predicted_low']} m to {facts['predicted_high']} m (the median landed {where} it)"
        )
    lines.append(f"Problems in the flight notes: {', '.join(facts.get('issues') or []) or 'none'}")
    return "\n".join(lines)


_PROBLEM_WORDS = ("issue", "problem", "recurring", "stall", "dive", "spiral", "veer", "flutter", "tumble", "inconsistent")
_OUTSIDE_WORDS = ("outside", "exceed", "beyond", "above the", "below the", "short of", "missed")
_INSIDE_WORDS = ("inside", "within", "matched", "as predicted")
_FACT_LINE = re.compile(r"^[A-Z][\w' ]{2,60}: ")
# Matches "the median distance increased", "distance dropped to" and so on. Only the
# distance is checked, because "the wing span was reduced" is about the change itself.
_DISTANCE_UP = re.compile(r"\b(?:distance|median)\b[^.]{0,30}?\b(?:increased|rose|improved|went up|grew)\b", re.I)
_DISTANCE_DOWN = re.compile(r"\b(?:distance|median)\b[^.]{0,30}?\b(?:decreased|dropped|fell|went down|declined)\b", re.I)


# Three flights can't show why something happened, so cause words get a note rejected.
# "resulting in a median distance of" is fine; "resulting in a stall" is a guess.
_CAUSE = re.compile(
    r"\b(?:caus\w*|because|due to|led to|leading to)\b"
    r"|\bresult(?:ing|ed)? in an? (?:stall|nose|spiral|veer|flutter|tumble)"
    r"|\b(?:stall|dive|spiral|veer|flutter|tumble)\w*\b[^.]{0,40}\bresult",
    re.I,
)


def _wrong_direction(text: str, facts: dict[str, Any]) -> bool:
    before = facts.get("parent_median_m")
    if before is None or before == facts["median_m"]:
        return False
    wrong = _DISTANCE_DOWN if facts["median_m"] > before else _DISTANCE_UP
    return wrong.search(text) is not None


def _clean_reply(text: str) -> str:
    """Small models sometimes echo the fact lines back; keep only the prose."""
    kept = [line.strip() for line in text.strip().strip('"').splitlines() if line.strip() and not _FACT_LINE.match(line)]
    return " ".join(kept)


def numbers_are_grounded(text: str, facts: dict[str, Any]) -> bool:
    """True if every number in `text` appears in the facts, with the same unit when one is given."""
    rendered = render_facts(facts)
    with_units = {(n, u) for n, u in _NUMBER.findall(rendered) if u}
    bare = {n for n, _ in _NUMBER.findall(rendered)}
    bare |= {str(int(float(n))) for n in list(bare)}
    for number, unit in _NUMBER.findall(text):
        if unit and (number, unit) not in with_units:
            return False
        if number not in bare:
            return False
    return True


def template_lab_note(facts: dict[str, Any]) -> str:
    parts = [f"Experiment #{facts['number']} flew a median of {facts['median_m']} m over {facts['flights']} flights."]
    if facts.get("changed"):
        before = facts.get("parent_median_m")
        change = f"Changing {facts['changed']}"
        if before is not None:
            parts.append(f"{change} moved the median from {before} m to {facts['median_m']} m.")
        else:
            parts.append(f"{change} was the only difference from the plane before it.")
    if facts.get("predicted_low") is not None:
        verdict = "inside" if facts["inside_prediction"] else "outside"
        parts.append(
            f"That landed {verdict} the predicted range of {facts['predicted_low']}–{facts['predicted_high']} m."
        )
    if facts.get("issues"):
        parts.append(f"Notes mention: {', '.join(facts['issues'])}.")
    return " ".join(parts)


async def write_lab_note(facts: dict[str, Any]) -> tuple[str, str]:
    """Returns (note, source). Falls back to a template if Gemma is down or invents numbers."""
    prompt = (
        "Write a lab notebook entry about this paper airplane test in at most two short sentences. "
        "Say what changed and what happened to the distance. Mention a problem only if one is listed "
        "under 'Problems in the flight notes'. Use only these facts. Copy every number exactly with its unit; "
        "distances are in metres (m). Don't guess at causes. Don't add numbers, advice, hype or emojis. "
        "Reply with the sentences only, not the facts.\n\n"
        f"Facts:\n{render_facts(facts)}"
    )
    try:
        text = _clean_reply(await _chat(prompt))
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.info("Gemma lab note unavailable: %s", exc)
        return template_lab_note(facts), "template"
    lower = text.lower()
    invents_problem = not facts.get("issues") and any(w in lower for w in _PROBLEM_WORDS)
    contradicts = False
    if facts.get("predicted_low") is not None:
        wrong_words = _OUTSIDE_WORDS if facts.get("inside_prediction") else _INSIDE_WORDS
        contradicts = any(w in lower for w in wrong_words)
    contradicts = contradicts or _wrong_direction(text, facts) or _CAUSE.search(text) is not None
    if not text or len(text) > 400 or invents_problem or contradicts or not numbers_are_grounded(text, facts):
        log.info("Rejected Gemma lab note: %r", text)
        return template_lab_note(facts), "template"
    return text, "gemma"


async def check_photo(image: bytes) -> dict[str, Any]:
    prompt = (
        "This is a photo of a folded paper airplane. Estimate: are the two wings symmetric "
        "(even/uneven/unclear)? Is the nose sharp or blunt? Are there folded-up winglets? "
        "Give a one-sentence comment a builder could act on, and your confidence from 0 to 1. "
        "If the photo is not a paper airplane, say unclear and give confidence 0."
    )
    data = json.loads(await _chat(prompt, _PHOTO_SCHEMA, image=image))
    confidence = float(data.get("confidence", 0))
    return {
        "symmetry": data.get("symmetry", "unclear"),
        "nose": data.get("nose", "unclear"),
        "winglets_visible": bool(data.get("winglets_visible", False)),
        "comment": str(data.get("comment", ""))[:300],
        "confidence": min(max(confidence, 0.0), 1.0),
        "estimate": True,
    }
