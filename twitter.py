"""
twitter.py — Post qualifying on-chain messages to Twitter/X via API v2.
"""

import hashlib
import logging
import os
from collections import deque

import tweepy

logger = logging.getLogger(__name__)

# Twitter API v2 free tier: 1,500 tweets/month
MONTHLY_TWEET_LIMIT = 1_500
WARN_AT = 1_400

# Rolling dedup window (last N message hashes)
DEDUP_WINDOW = 1_000

# Tweet body: message + blank line + URL
# A t.co-wrapped URL is always 23 chars; leave room for \n\n (2 chars)
URL_RESERVED = 23 + 2
MAX_TWEET_CHARS = 280


def _build_client() -> tweepy.Client:
    return tweepy.Client(
        bearer_token=os.environ["TWITTER_BEARER_TOKEN"],
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_SECRET"],
        wait_on_rate_limit=True,
    )


class TwitterPoster:
    def __init__(self) -> None:
        self._client = _build_client()
        self._tweet_count = 0
        self._seen: deque[str] = deque(maxlen=DEDUP_WINDOW)

    def _is_duplicate(self, text: str) -> bool:
        h = hashlib.sha256(text.encode()).hexdigest()
        if h in self._seen:
            return True
        self._seen.append(h)
        return False

    def _format_tweet(self, message: str, url: str) -> str:
        max_msg = MAX_TWEET_CHARS - URL_RESERVED - len(url) + 23  # url slot is 23 fixed
        # Simpler: max message chars = 280 - 2 (\n\n) - len(url)
        max_msg = MAX_TWEET_CHARS - 2 - len(url)
        if len(message) > max_msg:
            message = message[: max_msg - 1] + "…"
        return f"{message}\n\n{url}"

    def post(self, message: str, url: str, lang: str, chain: str, tx_hash: str) -> bool:
        """
        Post a tweet. Returns True if posted, False if skipped (duplicate or limit reached).
        """
        if self._tweet_count >= MONTHLY_TWEET_LIMIT:
            logger.warning("Monthly tweet limit reached — skipping post.")
            return False

        if self._is_duplicate(message):
            logger.debug(f"Duplicate message skipped: {message[:60]!r}")
            return False

        tweet_text = self._format_tweet(message, url)

        try:
            self._client.create_tweet(text=tweet_text)
            self._tweet_count += 1
            logger.info(
                f"[{chain}] Tweeted ({lang}) tx={tx_hash[:12]}… "
                f"[{self._tweet_count}/{MONTHLY_TWEET_LIMIT}]: {message[:60]!r}"
            )
            if self._tweet_count >= WARN_AT:
                logger.warning(
                    f"Approaching monthly tweet limit: {self._tweet_count}/{MONTHLY_TWEET_LIMIT}"
                )
            return True
        except tweepy.TweepyException as exc:
            logger.error(f"Failed to post tweet: {exc}")
            return False
