"""
chain.py — Block poller for EVM chains (Ethereum, Base) via Alchemy.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator

from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

logger = logging.getLogger(__name__)

STATE_FILE = Path("data/state.json")

CHAINS: dict[str, dict] = {
    "ethereum": {
        "rpc": "https://eth-mainnet.g.alchemy.com/v2/{key}",
        "explorer": "https://etherscan.io/tx/",
        "poll_interval": 12,  # seconds
    },
    "base": {
        "rpc": "https://base-mainnet.g.alchemy.com/v2/{key}",
        "explorer": "https://basescan.org/tx/",
        "poll_interval": 2,  # Base has ~2s block time
    },
}


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


async def poll_chain(
    chain_name: str,
    start_block: int | None = None,
) -> AsyncIterator[tuple[str, str, bytes]]:
    """
    Async generator that yields (tx_hash, chain_name, calldata) for every
    transaction in each new block on the given chain.

    start_block: if provided, overrides state.json and begins processing from
                 this block number (inclusive). Useful for dry-run / replay.
    """
    api_key = os.environ["ALCHEMY_API_KEY"]
    config = CHAINS[chain_name]
    rpc_url = config["rpc"].format(key=api_key)
    poll_interval = config["poll_interval"]

    w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))

    state = _load_state()

    if start_block is not None:
        last_block: int | None = start_block - 1
        logger.info(f"[{chain_name}] Starting poller from block {start_block} (override)")
    else:
        last_block = state.get(chain_name)
        logger.info(f"[{chain_name}] Starting poller (last block: {last_block})")

    while True:
        try:
            latest = await w3.eth.block_number

            if last_block is None:
                last_block = latest - 1

            if latest <= last_block:
                await asyncio.sleep(poll_interval)
                continue

            for block_num in range(last_block + 1, latest + 1):
                try:
                    block = await w3.eth.get_block(block_num, full_transactions=True)
                except Exception as exc:
                    logger.warning(f"[{chain_name}] Failed to fetch block {block_num}: {exc}")
                    continue

                for tx in block.transactions:
                    calldata: bytes = tx.get("input", b"") or b""
                    if calldata:
                        tx_hash = tx["hash"].hex()
                        yield tx_hash, chain_name, calldata

                last_block = block_num
                state[chain_name] = last_block
                _save_state(state)
                logger.info(f"[{chain_name}] Processed block {block_num}")

        except Exception as exc:
            logger.error(f"[{chain_name}] Poller error: {exc}")

        await asyncio.sleep(poll_interval)


def explorer_url(chain_name: str, tx_hash: str) -> str:
    return CHAINS[chain_name]["explorer"] + tx_hash
