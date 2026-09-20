from app.services import openai_state_store


def test_read_balance_defaults_to_zero_when_no_file() -> None:
    assert openai_state_store.read_balance() == 0.0


def test_set_balance_then_read_round_trips() -> None:
    openai_state_store.set_balance(25.0)
    assert openai_state_store.read_balance() == 25.0


def test_decrement_balance_subtracts_and_persists() -> None:
    openai_state_store.set_balance(1.0)
    new_balance = openai_state_store.decrement_balance(0.03)
    assert new_balance == 0.97
    assert openai_state_store.read_balance() == 0.97
