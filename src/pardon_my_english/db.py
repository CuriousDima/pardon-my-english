"""Account storage."""

import os

from sqlalchemy import BigInteger, inspect, text, update
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from pardon_my_english.llm import DEFAULT_MODEL, Model

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
    model: Model = Field(default=DEFAULT_MODEL)
    tokens_balance: int = Field(default=_NUM_TOKENS_DEFAULT)
    # Whether the user is a friend of the bot owner.
    # This is used to give the user an unlimited token balance.
    is_friend: bool = Field(default=False)


class DBClient:
    def __init__(self, db_url: str, echo: bool = False) -> None:
        self.engine = create_engine(normalize_db_url(db_url), echo=echo)
        SQLModel.metadata.create_all(self.engine)
        self._migrate()

    def _migrate(self) -> None:
        """Bring an existing database up to date. Runs on every startup; a no-op once migrated."""
        table = Account.__table__.name  # ty: ignore[unresolved-attribute]
        columns = {column["name"] for column in inspect(self.engine).get_columns(table)}
        with self.engine.begin() as connection:
            # Accounts used to pick a provider (OpenAI, Ollama, ...); only OpenRouter is left.
            if "provider" in columns:
                connection.execute(text(f"ALTER TABLE {table} DROP COLUMN provider"))
            # Enums are stored by member name, so rows on a removed model would fail to load.
            connection.execute(
                update(Account)
                .where(col(Account.model).not_in(list(Model)))
                .values(model=DEFAULT_MODEL)
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
