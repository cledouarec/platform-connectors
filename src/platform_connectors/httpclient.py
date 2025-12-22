"""Client to communicate with Http."""

import logging
from typing import Any
from urllib.parse import urlparse

from aiohttp import BasicAuth, ClientSession
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

#: Create logger for this file.
logger = logging.getLogger()


class HttpClient:
    """Provide an interface to Http server."""

    def __init__(
        self,
        http_url: str,
        auth: BasicAuth | None = None,
        headers: dict | None = None,
    ):
        """Construct the Http client.

        Args:
            http_url: URL to connect to Http server.
            auth: Authentication to connect to server.
            headers: Headers used for all sessions.

        Raises:
            ValueError: If URL is empty or invalid.

        """
        logger.debug("Create Http client")

        if not http_url:
            msg = "Http URL is invalid"
            raise ValueError(msg)

        # Validate URL format
        parsed = urlparse(http_url)
        if not parsed.scheme or not parsed.netloc:
            msg = f"Http URL is malformed: {http_url}"
            raise ValueError(msg)

        self._url: str = http_url

        self._auth: BasicAuth | None = auth
        self._headers: dict | None = headers
        self._session: ClientSession | None = None

        logger.debug("Http client created")

    async def __aenter__(self) -> "HttpClient":
        """Create Http session to send multiple requests.

        Returns:
            The HttpClient instance.

        """
        self._session = ClientSession(
            auth=self._auth,
            headers=self._headers,
            raise_for_status=True,
        )
        return self

    async def __aexit__(self, *err):
        """Close Http session.

        Args:
            *err: Exception information if an error occurred.

        """
        await self._session.close()
        self._session = None

    @retry(
        wait=wait_random_exponential(),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
    )
    async def get(
        self,
        suffix_url: str,
        **kwargs: Any,
    ) -> dict:
        """Send a GET request.

        Args:
            suffix_url: Last part of the URL contains the request.
            **kwargs: Additional parameters for the request (e.g., headers,
                params).

        Returns:
            Response with headers and content.

        """
        if self._session:
            async with self._session.get(
                url=self._url + suffix_url,
                **kwargs,
            ) as response:
                content = await response.json()
                return {"headers": response.headers, "content": content}
        else:
            async with (
                ClientSession(
                    auth=self._auth,
                    headers=self._headers,
                    raise_for_status=True,
                ) as session,
                session.get(
                    url=self._url + suffix_url,
                    **kwargs,
                ) as response,
            ):
                content = await response.json()
                return {"headers": response.headers, "content": content}

    @retry(
        wait=wait_random_exponential(),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
    )
    async def post(
        self,
        suffix_url: str,
        **kwargs: Any,
    ) -> dict:
        """Send a POST request.

        Args:
            suffix_url: Last part of the URL contains the request.
            **kwargs: Additional parameters for the request (e.g., headers,
                json, data).

        Returns:
            Response content.

        """
        if self._session:
            async with self._session.post(
                url=self._url + suffix_url,
                **kwargs,
            ) as response:
                return await response.json()
        else:
            async with (
                ClientSession(
                    auth=self._auth,
                    headers=self._headers,
                    raise_for_status=True,
                ) as session,
                session.post(
                    url=self._url + suffix_url,
                    **kwargs,
                ) as response,
            ):
                return await response.json()

    @retry(
        wait=wait_random_exponential(),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
    )
    async def put(
        self,
        suffix_url: str,
        **kwargs: Any,
    ) -> dict:
        """Send a PUT request.

        Args:
            suffix_url: Last part of the URL contains the request.
            **kwargs: Additional parameters for the request (e.g., headers,
                json, data).

        Returns:
            Response content.

        """
        if self._session:
            async with self._session.put(
                url=self._url + suffix_url,
                **kwargs,
            ) as response:
                return await response.json()
        else:
            async with (
                ClientSession(
                    auth=self._auth,
                    headers=self._headers,
                    raise_for_status=True,
                ) as session,
                session.put(
                    url=self._url + suffix_url,
                    **kwargs,
                ) as response,
            ):
                return await response.json()

    async def delete(
        self,
        suffix_url: str,
        **kwargs: Any,
    ) -> None:
        """Send a DELETE request.

        Args:
            suffix_url: Last part of the URL contains the request.
            **kwargs: Additional parameters for the request (e.g., headers,
                json, data).

        """
        if self._session:
            async with self._session.delete(
                url=self._url + suffix_url,
                **kwargs,
            ) as response:
                await response.read()
        else:
            async with (
                ClientSession(
                    auth=self._auth,
                    headers=self._headers,
                    raise_for_status=True,
                ) as session,
                session.delete(
                    url=self._url + suffix_url,
                    **kwargs,
                ) as response,
            ):
                await response.read()
