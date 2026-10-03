import os
import sys
from operator import attrgetter

from cachetools import TTLCache, cachedmethod
from sqlalchemy import BigInteger, text
from sqlmodel import Field, Session, SQLModel, create_engine, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common.llm_client import VALID_PROVIDER_MODEL_COMBINATIONS, Model, Provider

_NUM_TOKENS_DEFAULT = 1_000_000


def _normalize_db_url(db_url: str) -> str:
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
    provider: Provider = Field(default=Provider.OPENROUTER)
    model: Model = Field(default=Model.GPT54)
    tokens_balance: int = Field(default=_NUM_TOKENS_DEFAULT)
    # Whether the user is a friend of the bot owner.
    # This is used to give the user an unlimited token balance.
    is_friend: bool = Field(default=False)


class DBClient:
    def __init__(self, db_url: str, echo=True) -> None:
        self.engine = create_engine(_normalize_db_url(db_url), echo=echo)
        self._cache = TTLCache(maxsize=1024, ttl=60 * 60 * 4)  # 4 hours
        SQLModel.metadata.create_all(self.engine)
        self._reset_unsupported_models()

    def __del__(self) -> None:
        if hasattr(self, "engine"):
            self.engine.dispose()

    def _reset_unsupported_models(self) -> None:
        """Move accounts on a removed provider/model (e.g. direct OpenAI) to the defaults.

        Enums are stored by member name, so rows with names that no longer exist
        would fail to load. This runs on every startup and is a no-op once migrated.
        """
        valid_pairs = " OR ".join(
            f"(provider = '{provider.name}' AND model = '{model.name}')"
            for provider, model in sorted(
                VALID_PROVIDER_MODEL_COMBINATIONS, key=lambda pair: pair[0].name
            )
        )
        default_provider = Account.model_fields["provider"].default
        default_model = Account.model_fields["model"].default
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE {Account.__tablename__} "
                    "SET provider = :provider, model = :model "
                    f"WHERE NOT ({valid_pairs})"
                ),
                {"provider": default_provider.name, "model": default_model.name},
            )

    @cachedmethod(cache=attrgetter("_cache"))
    def get_or_create_account(
        self, user_id: int, username: str | None = None
    ) -> Account:
        with Session(self.engine) as session:
            statement = select(Account).filter(Account.user_id == user_id)  # ty: ignore[invalid-argument-type]
            account = session.exec(statement).one_or_none()
            if account is None:
                account = Account(user_id=user_id, username=username)
                session.add(account)
                session.commit()
                session.refresh(account)
            return account

    def decrease_token_balance(self, account: Account, num_tokens: int) -> None:
        with Session(self.engine) as session:
            account.tokens_balance -= num_tokens
            session.add(account)
            session.commit()
            session.refresh(account)
