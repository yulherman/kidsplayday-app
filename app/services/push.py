"""Expo Push API wrapper.

Sends push notifications via https://exp.host/--/api/v2/push/send.
Free tier; max 100 notifications per request, ~600 req/sec rate limit.
Docs: https://docs.expo.dev/push-notifications/sending-notifications/
"""
import logging
from typing import Iterable

import httpx

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
BATCH_SIZE = 100


async def send_push(
    tokens: Iterable[str],
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    """Fire-and-forget push send. Logs errors but does not raise."""
    token_list = [t for t in tokens if t and t.startswith("ExponentPushToken")]
    if not token_list:
        return

    messages = [
        {
            "to": token,
            "title": title,
            "body": body,
            "sound": "default",
            "data": data or {},
        }
        for token in token_list
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(0, len(messages), BATCH_SIZE):
            batch = messages[i : i + BATCH_SIZE]
            try:
                resp = await client.post(
                    EXPO_PUSH_URL,
                    json=batch,
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip, deflate",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code >= 400:
                    logger.warning(
                        "Expo push batch failed status=%s body=%s",
                        resp.status_code,
                        resp.text[:500],
                    )
            except httpx.HTTPError:
                logger.exception("Expo push request error")
