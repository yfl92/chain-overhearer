"""
main.py — chain-overhearer entry point.

Polls Ethereum and Base blocks, detects human-readable English/Chinese
messages in transaction calldata, and posts them to Twitter.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from chain import CHAINS, explorer_url, poll_chain
from detector import extract_message
from twitter import TwitterPoster

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def process_chain(chain_name: str, poster: TwitterPoster) -> None:
    logger.info(f"Starting chain processor: {chain_name}")
    async for tx_hash, chain, calldata in poll_chain(chain_name):
        result = extract_message(calldata)
        if result is None:
            continue
        text, lang = result
        url = explorer_url(chain, tx_hash)
        poster.post(text, url, lang=lang, chain=chain, tx_hash=tx_hash)


async def main() -> None:
    # Validate required env vars early
    required = [
        "ALCHEMY_API_KEY",
        "TWITTER_BEARER_TOKEN",
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    poster = TwitterPoster()

    tasks = [
        asyncio.create_task(process_chain(chain_name, poster))
        for chain_name in CHAINS
    ]

    logger.info(f"chain-overhearer running on chains: {', '.join(CHAINS)}")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
