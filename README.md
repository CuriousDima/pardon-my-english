# PardonMyEnglish
The Telegram bot comes with preset prompts to help you sound like a native speaker!

## Development

### Setup

```bash
virtualenv ve --python=python3.8
source ve/bin/activate
pip install -r requirements.txt
```

Add a `.env` file with the following content:

```bash
OPENAI_API_KEY=<your_openai_api_key>
ASTRA_SECURE_CONNECT_BUNDLE_PATH=<path_to_your_astra_secure_connect_bundle>
ASTRA_CLIENT_ID=<your_astra_client_id>
ASTRA_SECRET=<your_astra_secret>
```

### Astra configuration

0. Sign up at https://astra.datastax.com/, create a database, and keyspace `pardon_my_english`, and a table with the following schema:

```sql
CREATE TABLE openai_keys_by_user (
    user_id bigint PRIMARY KEY,
    openai_key text
);
```
1. Download the secure connect bundle from the Astra `Connect` tab.
2. Generate `Read/Write Service Account` in the same tab.

### Test

```bash
python bot/astra_client.py
python bot/llm_client.py
```