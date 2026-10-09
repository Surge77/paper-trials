import json

import pytest

from papertrials import gemma


def test_keyword_fallback_finds_common_problems() -> None:
    issues = gemma.issues_from_keywords("Climbed then stalled, and it veered left at the end")
    assert issues == ["stall", "veer_left"]


def test_keyword_fallback_returns_nothing_for_a_clean_flight() -> None:
    assert gemma.issues_from_keywords("smooth glide, landed flat") == []


async def test_empty_note_is_not_sent_anywhere() -> None:
    assert await gemma.parse_note("   ") == ([], None)


async def test_note_parsing_falls_back_to_keywords_when_ollama_is_down() -> None:
    issues, source = await gemma.parse_note("nose dive straight into the grass")
    assert source == "keywords"
    assert issues == ["nose_dive"]


async def test_gemma_issues_outside_the_allowed_list_are_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(prompt: str, schema: object = None, image: object = None) -> str:
        return json.dumps({"issues": ["stall", "exploded", "stall"]})

    monkeypatch.setattr(gemma, "_chat", fake_chat)
    assert await gemma.parse_note("went up and fell") == (["stall"], "gemma")


FACTS = {"number": 5, "flights": 3, "median_m": 14.2, "parent_median_m": 12.8, "predicted_low": 11.0, "predicted_high": 16.5,
         "inside_prediction": True}


def test_numbers_in_facts_are_grounded() -> None:
    assert gemma.numbers_are_grounded("Experiment 5 went from 12.8 m to 14.2 m.", FACTS)


def test_right_number_with_wrong_unit_is_not_grounded() -> None:
    assert not gemma.numbers_are_grounded("The median was 14.2 cm.", FACTS)


def test_invented_numbers_are_not_grounded() -> None:
    assert not gemma.numbers_are_grounded("It flew 19.4 m on the best throw.", FACTS)


async def test_lab_note_with_invented_number_is_replaced_by_template(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(prompt: str, schema: object = None, image: object = None) -> str:
        return "A new record of 25 m!"

    monkeypatch.setattr(gemma, "_chat", fake_chat)
    note, source = await gemma.write_lab_note(FACTS)
    assert source == "template"
    assert "14.2" in note and "25" not in note


async def test_lab_note_inventing_a_problem_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(prompt: str, schema: object = None, image: object = None) -> str:
        return "Median rose to 14.2 m. A recurring issue was inconsistent launches."

    monkeypatch.setattr(gemma, "_chat", fake_chat)
    assert (await gemma.write_lab_note(FACTS))[1] == "template"


async def test_lab_note_contradicting_the_prediction_check_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(prompt: str, schema: object = None, image: object = None) -> str:
        return "Median was 14.2 m, exceeding the predicted 11.0 m to 16.5 m."

    monkeypatch.setattr(gemma, "_chat", fake_chat)
    assert (await gemma.write_lab_note(FACTS))[1] == "template"


async def test_echoed_fact_lines_are_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(prompt: str, schema: object = None, image: object = None) -> str:
        return "Experiment number: 5\nMedian distance: 14.2 m\nMedian rose from 12.8 m to 14.2 m."

    monkeypatch.setattr(gemma, "_chat", fake_chat)
    assert await gemma.write_lab_note(FACTS) == ("Median rose from 12.8 m to 14.2 m.", "gemma")


async def test_grounded_lab_note_from_gemma_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(prompt: str, schema: object = None, image: object = None) -> str:
        return "Median rose from 12.8 m to 14.2 m across 3 flights."

    monkeypatch.setattr(gemma, "_chat", fake_chat)
    assert await gemma.write_lab_note(FACTS) == ("Median rose from 12.8 m to 14.2 m across 3 flights.", "gemma")


async def test_photo_check_is_marked_as_an_estimate_and_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_chat(prompt: str, schema: object = None, image: object = None) -> str:
        return json.dumps({"symmetry": "uneven", "nose": "sharp", "winglets_visible": False, "comment": "Left wing is lower.", "confidence": 3})

    monkeypatch.setattr(gemma, "_chat", fake_chat)
    result = await gemma.check_photo(b"fake")
    assert result["estimate"] is True
    assert result["confidence"] == 1.0
    assert result["symmetry"] == "uneven"
