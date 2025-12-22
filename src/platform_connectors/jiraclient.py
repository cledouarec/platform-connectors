"""Client to communicate with Jira.

This module provides an async client for interacting with Atlassian Jira
servers via REST API. It supports operations on issues, projects, users,
and custom fields with full JQL query support.

The client uses context managers for proper session lifecycle management,
includes automatic retry logic for transient failures, and provides convenient
methods for common Jira workflows.

Typical usage:
    import asyncio
    from jiraclient import JiraClient

    async def main():
        async with JiraClient(
            jira_url="https://my.jira.server.com",
            jira_username="user@example.com",
            jira_password="token"
        ) as jira_session:
            # Get issues from JQL query
            issues = await jira_session.tickets_from_jql(
                jql='project = TEST AND status = "To Do"'
            )

            # Get issue details
            issue = await jira_session.ticket("TEST-123")

            # Get changelogs details
            changelogs = await jira_session.changelogs_from_tickets(issues)

    asyncio.run(main())
"""

import asyncio
import logging
import math
from typing import ClassVar

from aiohttp import BasicAuth

from .httpclient import HttpClient

#: Create logger for this module.
logger = logging.getLogger(__name__)


class JiraClient:
    """Provide an interface to Jira server."""

    #: Version of Jira API used
    API_VERSION: int = 3

    #: Standard headers
    STANDARD_HEADERS: ClassVar[dict] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def __init__(
        self,
        jira_url: str,
        jira_username: str,
        jira_password: str,
    ) -> None:
        """Construct the Jira client.

        Args:
            jira_url: URL to connect to Jira.
            jira_username: Username to connect to Jira.
            jira_password: Password to connect to Jira.

        Raises:
            ValueError: If Jira credentials or URL are empty.

        """
        logger.debug("Create Jira client")

        if not jira_url:
            msg = "Jira URL is invalid"
            raise ValueError(msg)
        if not jira_username:
            msg = "Jira username is invalid"
            raise ValueError(msg)
        if not jira_password:
            msg = "Jira password is invalid"
            raise ValueError(msg)

        self._http_client: HttpClient = HttpClient(
            jira_url.rstrip("/") + f"/rest/api/{self.API_VERSION}/",
            BasicAuth(jira_username, jira_password),
        )

        logger.debug("Jira client created")

    async def __aenter__(self) -> "JiraClient":
        """Create session to send requests.

        Returns:
            The JiraClient instance.

        """
        await self._http_client.__aenter__()
        return self

    async def __aexit__(self, *err) -> None:
        """Close session."""
        await self._http_client.__aexit__(*err)

    async def _get_paginated(
        self,
        suffix_url: str,
        headers: dict,
        query: dict,
        result_field: str,
    ) -> list:
        """Send a GET request and aggregate the response.

        Args:
            suffix_url: Last part of the URL contains the request.
            headers: Header for the request.
            query: Query of the request.
            result_field: Field name containing results in response.

        Returns:
            Response data from all pages.

        """

        async def get_next_page(start_at):
            query["startAt"] = start_at
            response_ = await self._http_client.get(
                suffix_url,
                headers=headers,
                params=query,
            )
            return response_["content"][result_field]

        # Request first page to have the total of pages
        response = await self._http_client.get(
            suffix_url,
            headers=headers,
            params=query,
        )
        total_pages = math.ceil(
            response["content"]["total"] / query["maxResults"],
        )
        responses = response["content"][result_field]

        # Request all next pages in parallel
        tasks = [
            get_next_page(query["startAt"] + i * query["maxResults"])
            for i in range(1, total_pages)
        ]
        results = await asyncio.gather(*tasks)

        # Extract the responses
        next_responses = [item for sublist in results for item in sublist]
        responses.extend(next_responses)
        return responses

    async def ticket(
        self,
        key: str,
        fields: list[str] | str | None = None,
    ) -> dict:
        """Get ticket information from a given key.

        Args:
            key: Key of the ticket.
            fields: List of fields, for example: ['priority', 'summary'].

        Returns:
            Ticket information.

        """
        if fields is None:
            fields = "*all"

        query = {
            "fields": fields,
        }
        response = await self._http_client.get(
            f"issue/{key}",
            headers=self.STANDARD_HEADERS,
            params=query,
        )
        return response["content"]

    async def validate_jql(self, jql: str) -> None:
        """Validate JQL request.

        Args:
            jql: JQL request to validate.

        Raises:
            ValueError: If JQL is invalid.

        """
        query = {"queries": [jql]}
        response = await self._http_client.post(
            "jql/parse",
            headers=self.STANDARD_HEADERS,
            params=query,
        )
        if "errors" in response["queries"][0]:
            raise ValueError(response["queries"][0]["errors"][0])

    async def tickets_from_jql(
        self,
        jql: str,
        fields: list[str] | str | None = None,
    ) -> list:
        """Get tickets from a JQL request.

        Args:
            jql: JQL request to find tickets.
            fields: List of fields, for example: ['priority', 'summary'].

        Returns:
            Tickets list found.

        """
        if fields is None:
            fields = "*all"

        query = {
            "jql": jql,
            "fields": fields,
            "startAt": 0,
            "maxResults": 100,
            "expand": "renderedFields",
        }
        return await self._get_paginated(
            "search",
            headers=self.STANDARD_HEADERS,
            query=query,
            result_field="issues",
        )

    async def changelogs(self, key: str) -> list:
        """Get all changelogs of a given ticket.

        Args:
            key: Key of the ticket.

        Returns:
            Changelogs list.

        """
        query = {
            "startAt": 0,
            "maxResults": 100,
        }
        return await self._get_paginated(
            f"issue/{key}/changelog",
            headers=self.STANDARD_HEADERS,
            query=query,
            result_field="values",
        )

    async def changelogs_from_tickets(self, tickets: list) -> list:
        """Get changelogs information from a list of tickets.

        Args:
            tickets: List of tickets.

        Returns:
            List of changelogs information.

        """
        tasks = []
        for ticket in tickets:
            task = asyncio.create_task(self.changelogs(ticket["key"]))
            tasks.append(task)

        changelogs = await asyncio.gather(*tasks)

        return [
            {"key": ticket["key"], "changelog": changelog}
            for ticket, changelog in zip(tickets, changelogs, strict=True)
        ]

    async def parents_from_tickets(self, tickets: list) -> list:
        """Get parents information from a list of tickets.

        Args:
            tickets: List of tickets.

        Returns:
            List of parents information.

        """
        tasks = []
        for ticket in tickets:
            if ticket["fields"].get("parent"):
                task = asyncio.create_task(
                    self.ticket(ticket["fields"]["parent"]["key"]),
                )
                tasks.append(task)

        return await asyncio.gather(*tasks)

    async def versions(self, key: str) -> list:
        """Get all versions of a given project ordered by ranking.

        Args:
            key: Key of the project.

        Returns:
            Versions list.

        """
        query = {"startAt": 0, "maxResults": 100, "orderBy": "-sequence"}
        return await self._get_paginated(
            f"project/{key}/version",
            headers=self.STANDARD_HEADERS,
            query=query,
            result_field="values",
        )

    async def fields_information(self) -> list:
        """Get all fields information like id and associated display name.

        Returns:
            List of fields information.

        """
        response = await self._http_client.get(
            "field",
            headers=self.STANDARD_HEADERS,
        )
        return response["content"]
