from app.services.style_detection import detect_style


def test_detect_style_finds_exact_keyword() -> None:
    assert detect_style("une aquarelle de montagnes au lever du soleil") == "Aquarelle"


def test_detect_style_is_case_insensitive() -> None:
    assert detect_style("A CYBERPUNK city at night") == "Cyberpunk"


def test_detect_style_english_keyword() -> None:
    assert detect_style("a watercolor painting of a boat") == "Aquarelle"


def test_detect_style_returns_none_without_keyword() -> None:
    assert detect_style("un chat assis sur un mur") is None


def test_detect_style_prefers_longest_match_on_ambiguity() -> None:
    # "peinture" (Peinture à l'huile) et "aquarelle" (Aquarelle) sont tous les
    # deux présents ; le mot-clé le plus long/spécifique doit l'emporter.
    assert detect_style("une peinture aquarelle") == "Aquarelle"
