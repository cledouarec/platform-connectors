"""Unit tests for httpclient."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestServer

from platform_connectors import HttpClient


def test_create_http_client_with_empty_url() -> None:
    """Http client creation with invalid url must raise an exception."""
    with pytest.raises(ValueError, match="Http URL is invalid"):
        HttpClient("")


@pytest_asyncio.fixture
async def mock_server() -> AsyncGenerator[TestServer, None]:
    """Create a mock HTTP server for testing.

    Yields:
        TestServer: A test server instance for HTTP testing.

    """

    def handle_get(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "data": "test"})

    async def handle_post(request: web.Request) -> web.Response:
        data = await request.json()
        return web.json_response({"received": data})

    app = web.Application()
    app.router.add_get("/test", handle_get)
    app.router.add_post("/test", handle_post)

    server = TestServer(app)
    await server.start_server()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_http_client_get_request(mock_server: TestServer) -> None:
    """Test GET request with HttpClient."""
    async with HttpClient(str(mock_server.make_url("/"))) as client:
        response = await client.get("test")
        assert response["content"]["status"] == "ok"
        assert response["content"]["data"] == "test"


@pytest.mark.asyncio
async def test_http_client_post_request(mock_server: TestServer) -> None:
    """Test POST request with HttpClient."""
    async with HttpClient(str(mock_server.make_url("/"))) as client:
        response = await client.post("test", json={"key": "value"})
        assert response["received"]["key"] == "value"
