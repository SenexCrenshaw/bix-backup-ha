from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

EventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]
StatusCallback = Callable[[bool], Awaitable[None]]


class BixWsClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        ws_url: str,
        token: str,
        event_callback: EventCallback,
        status_callback: StatusCallback,
    ) -> None:
        self._session = session
        self._ws_url = ws_url
        self._token = token
        self._event_callback = event_callback
        self._status_callback = status_callback
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._socket: aiohttp.ClientWebSocketResponse | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="bix_backup_ws")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._socket is not None:
            await self._socket.close()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        backoff = 1
        while not self._stop_event.is_set():
            try:
                headers = {"Authorization": f"Bearer {self._token}"}
                async with self._session.ws_connect(
                    self._ws_url,
                    headers=headers,
                    heartbeat=30,
                    receive_timeout=90,
                ) as socket:
                    self._socket = socket
                    await self._status_callback(True)
                    backoff = 1
                    async for msg in socket:
                        if self._stop_event.is_set():
                            break
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            continue
                        payload = json.loads(msg.data)
                        if not isinstance(payload, dict):
                            continue
                        event_type = payload.get("type")
                        if isinstance(event_type, str):
                            await self._event_callback(event_type, payload)
            except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as err:
                _LOGGER.debug("BIX websocket disconnected: %s", err)
            finally:
                self._socket = None
                await self._status_callback(False)

            if self._stop_event.is_set():
                break
            await asyncio.sleep(min(backoff, 30))
            backoff = min(backoff * 2, 30)
