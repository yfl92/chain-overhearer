# chain-overhearer

A bot that listens to Ethereum and Base blocks and tweets any transaction that contains a human-readable message in English or Chinese.

## How it works

1. Polls new blocks on Ethereum and Base via Alchemy
2. Decodes each transaction's calldata as UTF-8
3. Runs language detection — keeps messages in English (`en`) or Chinese (`zh-cn` / `zh-tw`)
4. Posts qualifying messages to Twitter/X with a link to the transaction explorer

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# fill in your Alchemy API key and Twitter API credentials
```

You'll need:
- An [Alchemy](https://alchemy.com) account with API access to Ethereum and Base
- A [Twitter Developer](https://developer.twitter.com) app with **Read and Write** permissions and OAuth 1.0a credentials

### 3. Run

```bash
python main.py
```

## Deployment (Railway)

1. Push this repo to GitHub
2. Create a new Railway project from the repo
3. Add a **Persistent Volume** mounted at `/app/data`
4. Set all environment variables in the Railway Variables dashboard (same keys as `.env.example`)
5. Railway will build the Dockerfile and keep the bot running continuously

## Configuration

Chain config (RPC endpoints, explorers, poll intervals) lives in `chain.py`:

```python
CHAINS = {
    "ethereum": { ... },
    "base": { ... },
}
```

To add more EVM chains (e.g. Arbitrum, Optimism), add an entry there with the Alchemy RPC URL and the relevant block explorer base URL.

## Project structure

```
main.py        # entry point
chain.py       # block polling
detector.py    # calldata → language detection
twitter.py     # tweet posting
data/          # runtime state (gitignored)
```
