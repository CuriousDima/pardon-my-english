from operator import attrgetter

from cachetools import cachedmethod, TTLCache
from cachetools.keys import hashkey
from sqlalchemy import BigInteger
from sqlmodel import create_engine, SQLModel, Session, select, Field

from llm_client import Model, Provider

_NUM_TOKENS_DEFAULT = 1_000_000


class Account(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, sa_type=BigInteger)  # Telegram user ID
    username: str | None
    provider: Provider = Field(default=Provider.GROQ)
    model: Model = Field(default=Model.GEMMA)
    tokens_balance: int = Field(default=_NUM_TOKENS_DEFAULT)
    # Whether the user is a friend of the bot owner.
    # This is used to give the user an unlimited token balance.
    is_friend: bool = Field(default=False)


class DBClient:
    def __init__(self, db_url: str, echo=True) -> None:
        self.engine = create_engine(db_url, echo=echo)
        self._cache = TTLCache(maxsize=1024, ttl=60 * 60 * 4)  # 4 hours
        SQLModel.metadata.create_all(self.engine)

    def __del__(self) -> None:
        self.engine.dispose()

    @cachedmethod(cache=attrgetter("_cache"))
    def get_or_create_account(self, user_id: str, username=None) -> Account:
        with Session(self.engine) as session:
            statement = select(Account).filter(Account.user_id == user_id)
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
