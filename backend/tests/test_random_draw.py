import pytest

from app.services.random_draw import draw_random_index


def test_draw_random_index_within_bounds() -> None:
    for _ in range(200):
        index = draw_random_index(20)
        assert 1 <= index <= 20


def test_draw_random_index_single_option() -> None:
    assert draw_random_index(1) == 1


def test_draw_random_index_rejects_zero_or_negative() -> None:
    with pytest.raises(ValueError):
        draw_random_index(0)
    with pytest.raises(ValueError):
        draw_random_index(-1)


def test_draw_random_index_uses_randint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []

    def fake_randint(a: int, b: int) -> int:
        calls.append((a, b))
        return b

    monkeypatch.setattr("app.services.random_draw.random.randint", fake_randint)

    result = draw_random_index(20)

    assert calls == [(1, 20)]
    assert result == 20
