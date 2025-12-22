"""Client to communicate with GitLab.

This module provides an async client for interacting with GitLab servers
via REST API. It supports operations on projects, groups, merge requests,
pipelines, and commits with built-in rate limiting.

The client uses context managers for proper session lifecycle management,
includes automatic rate limiting to respect GitLab API quotas, and supports
parallel requests for efficient data retrieval.

Typical usage:
    import asyncio
    from datetime import datetime
    from platform_connectors import GitlabClient

    async def main():
        async with GitlabClient(
            gitlab_url="https://my.gitlab.server.com",
            gitlab_token="token"
        ) as gitlab_session:
            # Get all projects
            projects = await gitlab_session.projects()

            # Get merge requests with date filtering
            mrs = await gitlab_session.merge_requests(
                project_id=123,
                created_after=datetime(2024, 1, 1),
            )

            for mr in mrs:
                # Get full pipeline information
                pipelines = await gitlab_session.pipelines_from_merge_request(
                    project_id=mr["project_id"],
                    merge_request_id=mr["iid"],
                    full_info=True,
                )

                # Get merge request approvals
                approvals = await gitlab_session.approvals_from_merge_request(
                    project_id=mr["project_id"],
                    merge_request_id=mr["iid"],
                )

    asyncio.run(main())
"""

import asyncio
import logging
from datetime import datetime

from limiter import Limiter

from .httpclient import HttpClient

#: Create logger for this module.
logger = logging.getLogger(__name__)
# Force limiter logging level to INFO.
logging.getLogger("limiter").setLevel(logging.INFO)


class GitlabClient:
    """Provide an interface to GitLab server."""

    #: Version of GitLab API used
    API_VERSION: int = 4
    #: Requests per second rate
    LIMIT_REQUESTS_RATE: int = 30
    #: Total amount of requests available
    LIMIT_REQUESTS_CAPACITY: int = 1000
    #: Rate limiter for all GitLab requests
    limit_requests: Limiter = Limiter(
        rate=LIMIT_REQUESTS_RATE,
        capacity=LIMIT_REQUESTS_CAPACITY,
    )

    def __init__(
        self,
        gitlab_url: str,
        gitlab_token: str,
    ) -> None:
        """Construct the GitLab client.

        Args:
            gitlab_url: URL to connect to GitLab.
            gitlab_token: Token to connect to GitLab.

        Raises:
            ValueError: If URL or token are invalid.

        """
        logger.debug("Create GitLab client")

        if not gitlab_url:
            msg = "GitLab URL is invalid"
            raise ValueError(msg)
        if not gitlab_token:
            msg = "GitLab token is invalid"
            raise ValueError(msg)

        self._http_client: HttpClient = HttpClient(
            gitlab_url.rstrip("/") + f"/api/v{self.API_VERSION}/",
            headers={"PRIVATE-TOKEN": gitlab_token},
        )

        logger.debug("GitLab client created")

    async def __aenter__(self) -> "GitlabClient":
        """Create session to send requests.

        Returns:
            The GitlabClient instance.

        """
        await self._http_client.__aenter__()
        return self

    async def __aexit__(self, *err) -> None:
        """Close session."""
        await self._http_client.__aexit__(*err)

    @classmethod
    def get_rate_limit_status(cls) -> dict:
        """Get current rate limiter status.

        Returns:
            Dictionary with rate and available capacity.

        """
        return {
            "rate": cls.LIMIT_REQUESTS_RATE,
            "capacity": cls.LIMIT_REQUESTS_CAPACITY,
            "available": cls.limit_requests.available,
        }

    @limit_requests
    async def _get_paginated(
        self,
        suffix_url: str,
        query: dict,
    ) -> list:
        """Send a GET request and aggregate the response.

        Retrieves all pages of results in parallel to minimize API calls.

        Args:
            suffix_url: Last part of the URL for the request.
            query: Query parameters for the request.

        Returns:
            Aggregated response from all pages.

        """

        async def get_next_page(page: int) -> list:
            """Fetch a specific page of results.

            Args:
                page: Page number to retrieve.

            Returns:
                List of items from the page.

            """
            query["page"] = page
            response_ = await self._http_client.get(suffix_url, params=query)
            return response_["content"]

        # Request first page to determine total number of pages
        response = await self._http_client.get(suffix_url, params=query)
        total_pages = int(response["headers"]["x-total-pages"])
        responses = response["content"]

        # Fetch remaining pages in parallel
        if total_pages > 1:
            tasks = [
                get_next_page(query["page"] + i) for i in range(1, total_pages)
            ]
            results = await asyncio.gather(*tasks)

            # Flatten and extend results
            next_responses = [item for sublist in results for item in sublist]
            responses.extend(next_responses)

        return responses

    async def projects(self) -> list:
        """Get all projects.

        Returns:
            List of all accessible projects.

        """
        query = {
            "page": 1,
            "per_page": 100,
            "simple": "true",
            "membership": "true",
        }
        return await self._get_paginated("projects", query)

    async def groups(self) -> list:
        """Get all groups.

        Returns:
            List of all accessible groups.

        """
        query = {
            "page": 1,
            "per_page": 100,
            "min_access_level": 10,
        }
        return await self._get_paginated("groups", query)

    async def merge_requests(
        self,
        project_id: int | str,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list:
        """Get all merge requests for a project.

        Optionally filter by creation date range.

        Args:
            project_id: Identifier of the project.
            created_after: Filter results created after this date.
            created_before: Filter results created before this date.

        Returns:
            List of merge requests matching criteria.

        """
        query: dict = {
            "page": 1,
            "per_page": 100,
        }
        if created_after:
            query["created_after"] = created_after.isoformat()
        if created_before:
            query["created_before"] = created_before.isoformat()

        return await self._get_paginated(
            f"projects/{project_id}/merge_requests",
            query,
        )

    async def commits_from_merge_request(
        self,
        project_id: int | str,
        merge_request_id: int | str,
    ) -> list:
        """Get all commits from a merge request.

        Args:
            project_id: Identifier of the project.
            merge_request_id: Identifier of the merge request.

        Returns:
            List of commits in the merge request.

        """
        query = {
            "page": 1,
            "per_page": 100,
        }
        return await self._get_paginated(
            f"projects/{project_id}/merge_requests/{merge_request_id}/commits",
            query,
        )

    @limit_requests
    async def changes_from_merge_request(
        self,
        project_id: int | str,
        merge_request_id: int | str,
    ) -> list:
        """Get file changes from a merge request.

        Args:
            project_id: Identifier of the project.
            merge_request_id: Identifier of the merge request.

        Returns:
            List of file diffs in the merge request.

        """
        response = await self._http_client.get(
            f"projects/{project_id}/merge_requests/{merge_request_id}/diffs",
        )
        return response["content"]

    @limit_requests
    async def pipeline(
        self,
        project_id: int | str,
        pipeline_id: int | str,
    ) -> dict:
        """Get pipeline details from a pipeline identifier.

        Args:
            project_id: Identifier of the project.
            pipeline_id: Identifier of the pipeline.

        Returns:
            Pipeline information.

        """
        response = await self._http_client.get(
            f"projects/{project_id}/pipelines/{pipeline_id}",
        )
        return response["content"]

    async def pipelines_from_merge_request(
        self,
        project_id: int | str,
        merge_request_id: int | str,
        full_info: bool = False,
    ) -> list:
        """Get all pipelines from a merge request.

        Optionally retrieve full details for each pipeline by making
        additional API calls in parallel.

        Args:
            project_id: Identifier of the project.
            merge_request_id: Identifier of the merge request.
            full_info: If True, fetch complete pipeline details.

        Returns:
            List of pipelines, with full info if requested.

        """
        query = {
            "page": 1,
            "per_page": 100,
        }
        pipelines = await self._get_paginated(
            f"projects/{project_id}/merge_requests/"
            f"{merge_request_id}/pipelines",
            query,
        )

        if not full_info or not pipelines:
            return pipelines

        # Fetch full pipeline details in parallel
        pipelines_tasks = [
            asyncio.create_task(
                self.pipeline(project_id, pipeline["id"]),
            )
            for pipeline in pipelines
        ]

        return await asyncio.gather(*pipelines_tasks)

    @limit_requests
    async def approvals_from_merge_request(
        self,
        project_id: int | str,
        merge_request_id: int | str,
    ) -> dict:
        """Get approval status from a merge request.

        Args:
            project_id: Identifier of the project.
            merge_request_id: Identifier of the merge request.

        Returns:
            Approval information including rules and status.

        """
        response = await self._http_client.get(
            f"projects/{project_id}/merge_requests/"
            f"{merge_request_id}/approvals",
        )
        return response["content"]

    async def notes_from_merge_request(
        self,
        project_id: int | str,
        merge_request_id: int | str,
    ) -> list:
        """Get all notes/comments from a merge request.

        Args:
            project_id: Identifier of the project.
            merge_request_id: Identifier of the merge request.

        Returns:
            List of notes and comments on the merge request.

        """
        query = {
            "page": 1,
            "per_page": 100,
        }
        return await self._get_paginated(
            f"projects/{project_id}/merge_requests/{merge_request_id}/notes",
            query,
        )
