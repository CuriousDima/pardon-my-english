from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import os

from dotenv import load_dotenv

from cassandra.cluster import Cluster, Session
from cassandra.auth import PlainTextAuthProvider

ASTRA_CLIENT_ID_VAR_NAME: str = "ASTRA_CLIENT_ID"
ASTRA_SECRET_VAR_NAME: str = "ASTRA_SECRET"
ASTRA_SECURE_CONNECT_BUNDLE_PATH_VAR_NAME: str = "ASTRA_SECURE_CONNECT_BUNDLE_PATH"
ASTRA_KEYSPACE_VAR_NAME: str = "ASTRA_KEYSPACE"
ASTRA_TABLE_VAR_NAME: str = "ASTRA_TABLE"

ASTRA_KEYSPACE_DEFAULT: str = "pardon_my_english"
ASTRA_TABLE_DEFAULT: str = "openai_keys_by_user"


class DBClient(ABC):
    """Every DB client should implement this interface."""

    @abstractmethod
    def get_openai_key(self, user_id: int) -> Optional[str]:
        """
        Retrieves the OpenAI key associated with the given user ID.

        Args:
            user_id (int): The ID of the user.

        Returns:
            Optional[str]: The OpenAI key associated with the user, or None if no key is found.
        """
        pass

    @abstractmethod
    def set_openai_key(self, user_id: int) -> None:
        """
        Sets the OpenAI key for a specific user.

        Args:
            user_id (int): The ID of the user.
        """
        pass


@dataclass
class AstraDbConfig:
    client_id: str
    secret: str
    secure_connect_bundle_path: str
    keyspace: str = ASTRA_KEYSPACE_DEFAULT
    table: str = ASTRA_TABLE_DEFAULT


class AstraDBClient(DBClient):
    def __init__(self, config: AstraDbConfig) -> None:
        self._config = config
        self._session = self._get_session()

    def _get_session(self) -> Session:
        cloud_config = {
            "secure_connect_bundle": self._config.secure_connect_bundle_path
        }

        auth_provider = PlainTextAuthProvider(
            self._config.client_id, self._config.secret
        )
        cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
        return cluster.connect()

    def get_openai_key(self, user_id: int) -> str:
        """
        Retrieves the OpenAI key for the specified user.

        Args:
            user_id (int): The ID of the user.

        Returns:
            str: The OpenAI key associated with the user.

        Raises:
            ValueError: If the user with the specified ID is not found.
        """
        row = self._session.execute(
            f"""
            SELECT openai_key 
            FROM {self._config.keyspace}.{self._config.table} 
            WHERE user_id = {user_id}
            """
        ).one()
        if row:
            return row.openai_key

        raise ValueError(f"User with id {user_id} not found.")

    def set_openai_key(self, user_id: int) -> None:
        # TODO: Implement this method.
        pass


if __name__ == "__main__":
    load_dotenv()

    client_id: str = os.getenv(ASTRA_CLIENT_ID_VAR_NAME)
    if client_id is None:
        raise ValueError(f"Environment variable {ASTRA_CLIENT_ID_VAR_NAME} is not set.")
    secret: str = os.getenv(ASTRA_SECRET_VAR_NAME)
    if secret is None:
        raise ValueError(f"Environment variable {ASTRA_SECRET_VAR_NAME} is not set.")
    secure_connect_bundle_path: str = os.getenv(
        ASTRA_SECURE_CONNECT_BUNDLE_PATH_VAR_NAME
    )
    if secure_connect_bundle_path is None:
        raise ValueError(
            f"Environment variable {ASTRA_SECURE_CONNECT_BUNDLE_PATH_VAR_NAME} is not set."
        )

    keyspace: str = os.getenv(ASTRA_KEYSPACE_VAR_NAME, ASTRA_KEYSPACE_DEFAULT)
    table: str = os.getenv(ASTRA_TABLE_VAR_NAME, ASTRA_TABLE_DEFAULT)
    config = AstraDbConfig(
        client_id, secret, secure_connect_bundle_path, keyspace, table
    )

    astra_client = AstraDBClient(config)
    print(astra_client.get_openai_key(123))
    print(astra_client.get_openai_key(456))
