"""Client to communicate with Confluence.

This module provides an async client for interacting with Atlassian Confluence
servers via REST API. It supports operations on spaces, pages, folders, and
attachments.

The client uses context managers for proper session lifecycle management and
includes automatic error handling for common API failures.

Typical usage:

    import asyncio
    from platform_connectors import ConfluenceClient

    async def main():
        async with ConfluenceClient(
            confluence_url="https://my.confluence.server.com",
            confluence_username="user@example.com",
            confluence_password="token"
        ) as confluence_session:
            # Get space information
            space = await confluence_session.get_space_from_key("SPACE_1")

            # Create or update a page
            await confluence_session.create_or_update_page(
                space_id=space["id"],
                parent_page_id=123,
                title="My Page",
                message="Page content",
                representation="wiki"
            )

            # Upload attachment
            await confluence_session.upload_files(
                page_id=456,
                filenames=["file.pdf"]
            )

            # Search pages
            results = await confluence_session.search_pages(
                query='text ~ "keyword"',
                limit=50
            )

    asyncio.run(main())
"""

import logging
from typing import ClassVar

import aiofiles
from aiohttp import BasicAuth, FormData

from .httpclient import HttpClient

#: Create logger for this file.
logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Provide an interface to Confluence server."""

    #: Prefix to access Confluence API v1
    PREFIX_API_V1: str = "wiki/rest/api"

    #: Prefix to access Confluence API v2
    PREFIX_API_V2: str = "wiki/api/v2"

    #: Standard headers
    STANDARD_HEADERS: ClassVar[dict] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    #: No check headers
    NO_CHECK_HEADERS: ClassVar[dict] = {
        "X-Atlassian-Token": "no-check",
    }

    def __init__(
        self,
        confluence_url: str,
        confluence_username: str,
        confluence_password: str,
    ) -> None:
        """Construct the Confluence client.

        Args:
            confluence_url: URL to connect to Confluence.
            confluence_username: Username to connect to Confluence.
            confluence_password: Password to connect to Confluence.

        Raises:
            ValueError: If URL, username or password are invalid.

        """
        logger.debug("Create Confluence client")

        if not confluence_url:
            msg = "Confluence URL is invalid"
            raise ValueError(msg)
        if not confluence_username:
            msg = "Confluence username is invalid"
            raise ValueError(msg)
        if not confluence_password:
            msg = "Confluence password is invalid"
            raise ValueError(msg)

        self._http_client: HttpClient = HttpClient(
            confluence_url.rstrip("/") + "/",
            BasicAuth(confluence_username, confluence_password),
        )

        logger.debug("Confluence client created")

    async def __aenter__(self) -> "ConfluenceClient":
        """Create session to send requests.

        Returns:
            The ConfluenceClient instance.

        """
        await self._http_client.__aenter__()
        return self

    async def __aexit__(self, *err) -> None:
        """Close session."""
        await self._http_client.__aexit__(*err)

    async def get_space_from_id(self, space_id: int) -> dict:
        """Get all information about a space from identifier.

        Args:
            space_id: Identifier of the space.

        Returns:
            Space information if space is found.

        """
        response = await self._http_client.get(
            f"{self.PREFIX_API_V2}/spaces/{space_id}",
            headers=self.STANDARD_HEADERS,
        )
        return response["content"]

    async def get_space_from_key(self, space_key: str) -> dict:
        """Get all information about a space.

        Args:
            space_key: Key of the space.

        Returns:
            Space information if space is found.

        Raises:
            ValueError: If space is not found.

        """
        query = {
            "keys": [space_key],
        }
        response = await self._http_client.get(
            f"{self.PREFIX_API_V2}/spaces",
            headers=self.STANDARD_HEADERS,
            params=query,
        )
        if not response["content"]["results"]:
            msg = "Space not found"
            raise ValueError(msg)
        return response["content"]["results"][0]

    async def get_space_id_from_key(self, space_key: str) -> int:
        """Get a space identifier from space key.

        Args:
            space_key: Key of the space.

        Returns:
            Identifier of the space.

        """
        response = await self.get_space_from_key(space_key)
        return response["id"]

    async def get_page_from_id(self, page_id: int) -> dict:
        """Get a page from identifier.

        Args:
            page_id: Identifier of the page.

        Returns:
            Content if page is found.

        """
        query = {
            "body-format": "storage",
        }
        response = await self._http_client.get(
            f"{self.PREFIX_API_V2}/pages/{page_id}",
            headers=self.STANDARD_HEADERS,
            params=query,
        )
        return response["content"]

    async def get_page_from_title(self, space_id: int, title: str) -> dict:
        """Get a page from `title` in the given space.

        Args:
            space_id: Identifier of the space.
            title: Page title.

        Returns:
            Content if page is found.

        Raises:
            ValueError: If page is not found.

        """
        query = {
            "space-id": space_id,
            "title": title,
            "body-format": "storage",
        }
        response = await self._http_client.get(
            f"{self.PREFIX_API_V2}/pages",
            headers=self.STANDARD_HEADERS,
            params=query,
        )
        if not response["content"]["results"]:
            msg = "Page not found"
            raise ValueError(msg)
        return response["content"]["results"][0]

    async def get_page_id_from_title(self, space_id: int, title: str) -> int:
        """Get a page identifier from `title` in the given space.

        Args:
            space_id: Identifier of the space.
            title: Page title.

        Returns:
            Identifier of the page.

        """
        response = await self.get_page_from_title(space_id, title)
        return response["id"]

    async def get_page_version(self, page_id: int) -> int:
        """Get a page version from given page.

        Args:
            page_id: Identifier of the page.

        Returns:
            Version of the page.

        """
        page = await self.get_page_from_id(page_id)
        return page["version"]["number"]

    async def get_page_children(self, page_id: int) -> list:
        """Get child pages of the given page.

        Args:
            page_id: Identifier of the page.

        Returns:
            List of child pages.

        """
        query: dict = {
            "limit": 250,
        }
        response = await self._http_client.get(
            f"{self.PREFIX_API_V2}/pages/{page_id}/children",
            headers=self.STANDARD_HEADERS,
            params=query,
        )
        return response["content"]["results"]

    async def get_all_pages_in_space(self, space_id: int) -> list:
        """Get all pages in the given space.

        Args:
            space_id: Identifier of the space.

        Returns:
            List of pages.

        """
        query: dict = {
            "status": "current",
            "body-format": "storage",
            "limit": 250,
        }

        url = f"{self.PREFIX_API_V2}/spaces/{space_id}/pages"
        responses = []

        while url:
            response = await self._http_client.get(
                url,
                headers=self.STANDARD_HEADERS,
                params=query,
            )
            query = {}

            content = response["content"]
            responses.extend(content["results"])
            url = content["_links"].get("next")

        return responses

    async def create_or_update_page(
        self,
        space_id: int,
        parent_page_id: int,
        title: str,
        message: str,
        representation: str = "wiki",
    ) -> None:
        """Create or update page in the given space.

        The page will be located under `parent_page` with the given `title`
        and content `message` in the specified `representation` format.
        By default, Wiki markup format is used but "storage" can also be used.

        Args:
            space_id: Identifier of the space.
            parent_page_id: Identifier of the parent page.
            title: Page title.
            message: Page content.
            representation: Content format ("wiki" or "storage").

        Raises:
            ValueError: If parent page or representation format is invalid.

        """
        logger.debug("Create or update page")

        if representation not in ("storage", "wiki"):
            msg = "Representation must be 'storage' or 'wiki'"
            raise ValueError(msg)

        query = {
            "spaceId": space_id,
            "status": "current",
            "title": title,
            "parentId": parent_page_id,
            "body": {
                "representation": representation,
                "value": message,
            },
        }

        try:
            page_id = await self.get_page_id_from_title(space_id, title)
            query["id"] = page_id
            version = await self.get_page_version(page_id)
            query["version"] = {"number": version + 1, "message": ""}
            await self._http_client.put(
                f"{self.PREFIX_API_V2}/pages/{page_id}",
                headers=self.STANDARD_HEADERS,
                json=query,
            )
            logger.debug("Page updated")
        except ValueError:
            logger.debug("Page does not exist, creating new page")
            await self._http_client.post(
                f"{self.PREFIX_API_V2}/pages",
                headers=self.STANDARD_HEADERS,
                json=query,
            )
            logger.debug("New page created")

    async def upload_files(
        self,
        page_id: int,
        filenames: list[str],
    ) -> None:
        """Upload files and attach to the given page.

        Args:
            page_id: Identifier of the page.
            filenames: List of files to upload.

        """
        for filename in filenames:
            async with aiofiles.open(filename, mode="rb") as file:
                data = FormData()
                data.add_field(
                    "file",
                    await file.read(),
                    filename=filename,
                )

                await self._http_client.put(
                    f"{self.PREFIX_API_V1}/content/{page_id}/child/attachment",
                    headers=self.NO_CHECK_HEADERS,
                    data=data,
                )

    async def rename_page(
        self,
        page_id: int,
        new_title: str,
    ) -> None:
        """Rename page with given title.

        Args:
            page_id: Identifier of the page to rename.
            new_title: New page title.

        """
        logger.debug("Rename page")

        version = await self.get_page_version(page_id)
        query = {
            "id": page_id,
            "status": "current",
            "title": new_title,
            "version": {"number": version + 1, "message": ""},
        }
        await self._http_client.put(
            f"{self.PREFIX_API_V2}/pages/{page_id}",
            headers=self.STANDARD_HEADERS,
            json=query,
        )

        logger.debug("Page renamed")

    async def move_page(
        self,
        page_id: int,
        new_parent_page_id: int,
    ) -> None:
        """Move page under the given parent page.

        Args:
            page_id: Identifier of page to move.
            new_parent_page_id: Identifier of the new parent page.

        """
        logger.debug("Move page")

        await self._http_client.put(
            f"{self.PREFIX_API_V1}/content/{page_id}/move/append/{new_parent_page_id}",
            headers=self.STANDARD_HEADERS,
        )

        logger.debug("Page moved")

    async def delete_page(
        self,
        page_id: int,
    ) -> None:
        """Delete given page.

        Args:
            page_id: Identifier of page to delete.

        """
        logger.debug("Delete page")

        await self._http_client.delete(
            f"{self.PREFIX_API_V2}/pages/{page_id}",
            headers=self.STANDARD_HEADERS,
        )

        logger.debug("Page deleted")

    async def get_folder_from_id(self, folder_id: int) -> dict:
        """Get a folder from identifier.

        Args:
            folder_id: Identifier of the folder.

        Returns:
            Content if folder is found.

        """
        response = await self._http_client.get(
            f"{self.PREFIX_API_V2}/folders/{folder_id}",
            headers=self.STANDARD_HEADERS,
        )
        return response["content"]

    async def create_folder(
        self,
        space_id: int,
        parent_page_id: int,
        title: str,
    ) -> int:
        """Create folder in the given space.

        The folder will be located under the parent page with the given
        title.

        Args:
            space_id: Identifier of the space.
            parent_page_id: Identifier of the parent page.
            title: Folder title.

        Returns:
            Identifier of the created folder.

        """
        logger.debug("Create folder")

        query = {
            "spaceId": space_id,
            "title": title,
            "parentId": parent_page_id,
        }

        response = await self._http_client.post(
            f"{self.PREFIX_API_V2}/folders",
            headers=self.STANDARD_HEADERS,
            json=query,
        )

        logger.debug("New folder created")
        return response["id"]

    async def delete_folders(
        self,
        folder_id: int,
    ) -> None:
        """Delete given folder.

        Args:
            folder_id: Identifier of folder to delete.

        """
        logger.debug("Delete folder")

        await self._http_client.delete(
            f"{self.PREFIX_API_V2}/folders/{folder_id}",
            headers=self.STANDARD_HEADERS,
        )

        logger.debug("Folder deleted")

    async def get_user_from_id(self, user_id: int) -> dict:
        """Get all user information from identifier.

        Args:
            user_id: User identifier.

        Returns:
            User information.

        """
        query = {
            "accountId": [user_id],
        }
        response = await self._http_client.get(
            f"{self.PREFIX_API_V1}/user",
            headers=self.STANDARD_HEADERS,
            params=query,
        )
        return response["content"]

    async def search_pages(
        self,
        query: str,
        limit: int = 100,
    ) -> list:
        """Search for pages in Confluence.

        Args:
            query: Search query (CQL syntax).
            limit: Maximum number of results to return.

        Returns:
            List of pages matching the search query.

        """
        params = {
            "cql": query,
            "limit": limit,
        }

        response = await self._http_client.get(
            f"{self.PREFIX_API_V1}/search",
            headers=self.STANDARD_HEADERS,
            params=params,
        )
        return response["content"]["results"]
