"""Account storage."""

import os

from sqlalchemy import BigInteger, text, update
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from pardon_my_english.llm import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    VALID_PROVIDER_MODEL_COMBINATIONS,
    Model,
    Provider,
)

_NUM_TOKENS_DEFAULT = 1_000_000


def normalize_db_url(db_url: str) -> str:
    """Accept either a full SQLAlchemy URL or a path to a SQLite file."""
    db_url = db_url.strip()
    if not db_url:
        raise ValueError("DB_URI is empty.")
    if "://" in db_url:
        return db_url
    if db_url == ":memory:":
        return "sqlite:///:memory:"
    db_path = os.path.abspath(os.path.expanduser(db_url))
    return f"sqlite:///{db_path}"


class Account(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, sa_type=BigInteger)  # Telegram user ID
    username: str | None
    provider: Provider = Field(default=DEFAULT_PROVIDER)
    model: Model = Field(default=DEFAULT_MODEL)
    tokens_balance: int = Field(default=_NUM_TOKENS_DEFAULT)
    # Whether the user is a friend of the bot owner.
    # This is used to give the user an unlimited token balance.
    is_friend: bool = Field(default=False)


class DBClient:
    def __init__(self, db_url: str, echo: bool = False) -> None:
        self.engine = create_engine(normalize_db_url(db_url), echo=echo)
        SQLModel.metadata.create_all(self.engine)
        self._reset_unsupported_models()

    def _reset_unsupported_models(self) -> None:
        """Move accounts on a removed provider/model to the defaults.

        Enums are stored by member name, so rows with names that no longer exist
        would fail to load. This runs on every startup and is a no-op once migrated.
        """
        valid_pairs = " OR ".join(
            f"(provider = '{provider.name}' AND model = '{model.name}')"
            for provider, model in sorted(
                VALID_PROVIDER_MODEL_COMBINATIONS, key=lambda pair: pair[0].name
            )
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE {Account.__tablename__} "
                    "SET provider = :provider, model = :model "
                    f"WHERE NOT ({valid_pairs})"
                ),
                {"provider": DEFAULT_PROVIDER.name, "model": DEFAULT_MODEL.name},
            )

    def get_or_create_account(
        self, user_id: int, username: str | None = None
    ) -> Account:
        with Session(self.engine, expire_on_commit=False) as session:
            statement = select(Account).where(col(Account.user_id) == user_id)
            account = session.exec(statement).one_or_none()
            if account is None:
                account = Account(user_id=user_id, username=username)
                session.add(account)
                session.commit()
            elif username is not None and account.username != username:
                account.username = username
                session.add(account)
                session.commit()
            return account

    def decrease_token_balance(self, user_id: int, num_tokens: int) -> None:
        # Update in the database rather than from a loaded value, so concurrent edits
        # (e.g. the owner topping up a balance) are never overwritten.
        with self.engine.begin() as connection:
            connection.execute(
                update(Account)
                .where(col(Account.user_id) == user_id)
                .values(tokens_balance=col(Account.tokens_balance) - num_tokens)
            )
