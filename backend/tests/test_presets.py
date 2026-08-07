import logging

import pytest

from app.services.presets import load_presets, resolve_preset


def test_load_presets_has_default_and_all_styles() -> None:
    presets = load_presets()
    assert "default" in presets
    assert "Anime" in presets
    assert len(presets) == 21  # default + 20 styles


def test_resolve_preset_none_returns_default() -> None:
    preset = resolve_preset(None)
    assert preset == load_presets()["default"]


def test_resolve_preset_known_style() -> None:
    preset = resolve_preset("Anime")
    assert preset == load_presets()["Anime"]
    assert preset.checkpoint.startswith("REPLACE_ME_")


def test_resolve_preset_unknown_style_falls_back_to_default(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="app.services.presets"):
        preset = resolve_preset("Style Inexistant")

    assert preset == load_presets()["default"]
    assert "Style Inexistant" in caplog.text
