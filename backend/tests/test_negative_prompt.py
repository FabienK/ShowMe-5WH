from app.services.negative_prompt import strip_negative_conflicts

_NEGATIVE = "low quality, blurry, deformed, extra limbs, watermark"


def test_no_conflict_keeps_negative_prompt_unchanged() -> None:
    result = strip_negative_conflicts("un chat assis sur un mur", _NEGATIVE)
    assert result == _NEGATIVE


def test_explicit_request_strips_matching_term() -> None:
    result = strip_negative_conflicts("un portrait avec un flou artistique", _NEGATIVE)
    assert "blurry" not in result
    assert "low quality" in result
    assert "deformed" in result


def test_negation_keeps_term_in_negative_prompt() -> None:
    result = strip_negative_conflicts("un portrait net, sans flou", _NEGATIVE)
    assert result == _NEGATIVE


def test_watermark_trigger_strips_only_watermark() -> None:
    result = strip_negative_conflicts("une photo avec un filigrane visible", _NEGATIVE)
    assert "watermark" not in result
    assert "blurry" in result


def test_multiple_conflicts_strip_multiple_terms() -> None:
    result = strip_negative_conflicts(
        "une image avec un flou artistique et une signature visible", _NEGATIVE
    )
    assert "blurry" not in result
    assert "watermark" not in result
    assert "low quality" in result
    assert "deformed" in result
    assert "extra limbs" in result


def test_empty_negative_prompt_returns_empty() -> None:
    assert strip_negative_conflicts("peu importe le prompt", "") == ""
