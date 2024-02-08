import os

from dotenv import load_dotenv

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

ASTRA_CLIENT_ID_VAR_NAME: str = "ASTRA_CLIENT_ID"
ASTRA_SECRET_VAR_NAME: str = "ASTRA_SECRET"
ASTRA_SECURE_CONNECT_BUNDLE_PATH_VAR_NAME: str = "ASTRA_SECURE_CONNECT_BUNDLE_PATH"
ASTRA_KEYSPACE_VAR_NAME = "ASTRA_KEYSPACE"
ASTRA_TABLE_VAR_NAME = "ASTRA_TABLE"

ASTRA_KEYSPACE_DEFAULT: str = "pardon_my_english"
ASTRA_TABLE_DEFAULT: str = "openai_keys_by_user"

def get_session(client_id, client_secret, secure_connect_bundle):
    cloud_config = {
        'secure_connect_bundle': secure_connect_bundle
    }

    auth_provider = PlainTextAuthProvider(client_id, client_secret)
    cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
    return cluster.connect()


if __name__ == "__main__":
    load_dotenv()

    client_id: str = os.getenv(ASTRA_CLIENT_ID_VAR_NAME)
    if client_id is None:
        raise ValueError(f"Environment variable {ASTRA_CLIENT_ID_VAR_NAME} is not set.")
    secret: str = os.getenv(ASTRA_SECRET_VAR_NAME)
    if secret is None:
        raise ValueError(f"Environment variable {ASTRA_SECRET_VAR_NAME} is not set.")
    secure_connect_bundle_path: str = os.getenv(ASTRA_SECURE_CONNECT_BUNDLE_PATH_VAR_NAME)
    if secure_connect_bundle_path is None:
        raise ValueError(f"Environment variable {ASTRA_SECURE_CONNECT_BUNDLE_PATH_VAR_NAME} is not set.")

    keyspace: str = os.getenv(ASTRA_KEYSPACE_VAR_NAME, ASTRA_KEYSPACE_DEFAULT)
    table: str = os.getenv(ASTRA_TABLE_VAR_NAME, ASTRA_TABLE_DEFAULT)

    session = get_session(client_id, secret, secure_connect_bundle_path)

    row = session.execute(f"SELECT openai_key FROM {keyspace}.{table} WHERE user_id = 123").one()
    if row:
        print(row)
    else:
        print("An error occurred.")