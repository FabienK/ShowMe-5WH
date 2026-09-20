import logging

import pytest

from app.services.presets import load_style_models, resolve_model, resolve_style_models


def test_load_style_models_has_default_and_all_styles() -> None:
    styles = load_style_models()
    assert "default" in styles
    assert "Anime" in styles
    assert len(styles) == 21  # default + 20 styles


def test_every_style_has_at_least_one_model() -> None:
    for style, models in load_style_models().items():
        assert len(models) >= 1, style


def test_resolve_style_models_none_returns_default_plus_flux_variants() -> None:
    models = resolve_style_models(None)
    assert models[:-4] == load_style_models()["default"]
    assert models[-4].id == "flux_default"
    assert models[-4].engine_type == "flux"
    assert models[-3].id == "flux_schnell_default"
    assert models[-3].engine_type == "flux_schnell"
    assert models[-2].id == "flux_kontext_default"
    assert models[-2].engine_type == "flux_kontext"
    assert models[-1].id == "openai_default"
    assert models[-1].engine_type == "openai"


def test_resolve_style_models_known_style_adds_flux_variants_when_missing() -> None:
    models = resolve_style_models("Anime")
    assert models[:-4] == load_style_models()["Anime"]
    assert models[0].checkpoint == "Counterfeit-V2.5_fp16.safetensors"
    assert models[-4].id == "flux_anime"
    assert models[-4].engine_type == "flux"
    assert models[-3].id == "flux_schnell_anime"
    assert models[-3].engine_type == "flux_schnell"
    assert models[-2].id == "flux_kontext_anime"
    assert models[-2].engine_type == "flux_kontext"
    assert models[-1].id == "openai_anime"
    assert models[-1].engine_type == "openai"


def test_resolve_style_models_keeps_existing_flux_option_untouched_and_adds_schnell() -> None:
    models = resolve_style_models("Aquarelle")
    assert models[:-3] == load_style_models()["Aquarelle"]
    assert sum(1 for model in models if model.engine_type == "flux") == 1
    assert models[-3].id == "flux_schnell_aquarelle"
    assert models[-3].engine_type == "flux_schnell"
    assert models[-2].id == "flux_kontext_aquarelle"
    assert models[-2].engine_type == "flux_kontext"
    assert models[-1].id == "openai_aquarelle"
    assert models[-1].engine_type == "openai"


def test_resolve_style_models_flux_and_schnell_are_always_present() -> None:
    for style in load_style_models():
        models = resolve_style_models(style)
        assert any(model.engine_type == "flux" for model in models), style
        assert any(model.engine_type == "flux_schnell" for model in models), style
        assert any(model.engine_type == "flux_kontext" for model in models), style
        assert any(model.engine_type == "openai" for model in models), style


def test_resolve_style_models_unknown_style_falls_back_to_default(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.services.presets"):
        models = resolve_style_models("Style Inexistant")

    assert models[:-4] == load_style_models()["default"]
    assert models[-4].id == "flux_default"
    assert models[-3].id == "flux_schnell_default"
    assert models[-2].id == "flux_kontext_default"
    assert models[-1].id == "openai_default"
    assert "Style Inexistant" in caplog.text


def test_all_sd_checkpoint_models_have_a_real_checkpoint() -> None:
    for style, models in load_style_models().items():
        for model in models:
            if model.engine_type == "sd_checkpoint":
                assert model.checkpoint is not None, (style, model.id)
                assert not model.checkpoint.startswith("REPLACE_ME_"), (style, model.id)


def test_resolve_model_requires_model_id_now_that_flux_is_always_added() -> None:
    with pytest.raises(ValueError):
        resolve_model("Anime", None)


def test_resolve_model_requires_model_id_when_multiple() -> None:
    with pytest.raises(ValueError):
        resolve_model("Aquarelle", None)


def test_resolve_model_selects_by_id() -> None:
    model = resolve_model("Aquarelle", "flux_aquarelle")
    assert model.engine_type == "flux"


def test_resolve_model_selects_auto_added_flux_by_id() -> None:
    model = resolve_model("Anime", "flux_anime")
    assert model.engine_type == "flux"


def test_resolve_model_selects_auto_added_flux_schnell_by_id() -> None:
    model = resolve_model("Anime", "flux_schnell_anime")
    assert model.engine_type == "flux_schnell"


def test_resolve_model_rejects_unknown_model_id() -> None:
    with pytest.raises(ValueError):
        resolve_model("Aquarelle", "nope")


def test_resolve_model_none_style_requires_model_id_now_that_flux_is_added() -> None:
    with pytest.raises(ValueError):
        resolve_model(None, None)


def test_resolve_model_none_style_selects_generalist_by_id() -> None:
    model = resolve_model(None, "sdxl_default")
    assert model.id == "sdxl_default"


def test_photoreliste_and_cyberpunk_offer_flux_schnell_as_third_choice() -> None:
    for style in ("Photoréaliste", "Cyberpunk"):
        models = load_style_models()[style]
        assert len(models) == 3, style
        assert any(model.engine_type == "flux_schnell" for model in models), style


def test_resolve_model_selects_flux_schnell_by_id() -> None:
    model = resolve_model("Cyberpunk", "flux_schnell_cyberpunk")
    assert model.engine_type == "flux_schnell"


def test_resolve_model_selects_auto_added_flux_kontext_by_id() -> None:
    model = resolve_model("Anime", "flux_kontext_anime")
    assert model.engine_type == "flux_kontext"


def test_resolve_model_selects_auto_added_openai_by_id() -> None:
    model = resolve_model("Anime", "openai_anime")
    assert model.engine_type == "openai"
    assert model.checkpoint is None
    assert model.width == 1024
    assert model.height == 1024


def test_openai_is_always_present_even_for_single_model_styles() -> None:
    for style in load_style_models():
        models = resolve_style_models(style)
        assert sum(1 for model in models if model.engine_type == "openai") == 1, style
