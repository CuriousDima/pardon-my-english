import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import inspect, update
from sqlmodel import col

from pardon_my_english.db import Account, DBClient, normalize_db_url
from pardon_my_english.llm import Model


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "accounts.db"


def test_normalize_db_url(tmp_path: Path) -> None:
    assert normalize_db_url("postgresql://u@h/db") == "postgresql://u@h/db"
    assert normalize_db_url(":memory:") == "sqlite:///:memory:"
    assert normalize_db_url(f" {tmp_path}/a.db ") == f"sqlite:///{tmp_path}/a.db"
    with pytest.raises(ValueError):
        normalize_db_url("  ")


def test_get_or_create_account(db_path: Path) -> None:
    db = DBClient(str(db_path))

    account = db.get_or_create_account(user_id=42, username="old")
    assert account.model == Model.GPT6_LUNA
    assert account.tokens_balance == 1_000_000
    assert not account.is_friend

    again = db.get_or_create_account(user_id=42, username="new")
    assert again.id == account.id
    assert again.username == "new"


def test_decrease_token_balance_keeps_concurrent_changes(db_path: Path) -> None:
    db = DBClient(str(db_path))
    account = db.get_or_create_account(user_id=42)

    # The owner tops up the balance after the account was loaded.
    with db.engine.begin() as connection:
        connection.execute(
            update(Account)
            .where(col(Account.id) == account.id)
            .values(tokens_balance=5_000_000)
        )
    db.decrease_token_balance(user_id=42, num_tokens=100)

    assert db.get_or_create_account(user_id=42).tokens_balance == 4_999_900


def test_accounts_on_removed_models_are_migrated(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    connection.execute(
        "CREATE TABLE account (id INTEGER PRIMARY KEY, user_id BIGINT NOT NULL, "
        "username VARCHAR, provider VARCHAR NOT NULL, model VARCHAR NOT NULL, "
        "tokens_balance INTEGER NOT NULL, is_friend BOOLEAN NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO account (user_id, username, provider, model, tokens_balance, is_friend) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "openai", "OPENAI", "GPT54", 500, 0),
            (2, "old_openrouter", "OPENROUTER", "GPT54", 10, 1),
            (3, "ollama", "OLLAMA", "QWEN25_CODER_1_5B", 10, 0),
        ],
    )
    connection.commit()
    connection.close()

    db = DBClient(str(db_path))
    # Running the migration again is a no-op.
    db = DBClient(str(db_path))

    columns = {column["name"] for column in inspect(db.engine).get_columns("account")}
    assert "provider" not in columns
    expected_balances = {1: 500, 2: 10, 3: 10}
    for user_id, balance in expected_balances.items():
        account = db.get_or_create_account(user_id=user_id)
        assert (account.model, account.tokens_balance) == (Model.GPT6_LUNA, balance)
    # New accounts can still be created after the provider column is gone.
    assert db.get_or_create_account(user_id=4).model == Model.GPT6_LUNA
