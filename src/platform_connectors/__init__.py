"""Platform connectors module for retrieving data from various platforms.

This module provides async client classes to interact with:
- Jira: fetch issues and metadata
- Confluence: retrieve pages and space information
- GitLab: access repositories and merge requests
- Http: base HTTP client for platform communication

All clients require authentication credentials passed as constructor
parameters.

Example:
    import asyncio
    from platform_connectors import JiraClient, ConfluenceClient, GitlabClient

    async def main():
        # Jira example
        async with JiraClient(
            jira_url="https://my.jira.server.com",
            jira_username="user@example.com",
            jira_password="token"
        ) as jira_session:
            issues = await jira_session.tickets_from_jql(jql="project = TEST")
            changelogs = await jira_session.changelogs_from_tickets(issues)

        # GitLab example
        async with GitlabClient(
            gitlab_url="https://my.gitlab.server.com",
            gitlab_token="token"
        ) as gitlab_session:
            mrs = await gitlab_session.merge_requests(project_id=123)
            for mr in mrs:
                commits = await gitlab_session.commits_from_merge_request(
                    project_id=mr["project_id"],
                    merge_request_iid=mr["iid"]
                )

        # Confluence example
        async with ConfluenceClient(
            confluence_url="https://my.confluence.server.com",
            confluence_username="user@example.com",
            confluence_password="token"
        ) as confluence_session:
            space = await confluence_session.get_space_from_key(
                space_key="DOCS"
            )
            pages = await confluence_session.get_all_pages_in_space(
                space_id=space["id"]
            )

    asyncio.run(main())

"""

from typing import Final

from .confluenceclient import ConfluenceClient
from .gitlabclient import GitlabClient
from .httpclient import HttpClient
from .jiraclient import JiraClient

__version__ = "0.0.0"

__all__: Final[list[str]] = [
    "ConfluenceClient",
    "GitlabClient",
    "HttpClient",
    "JiraClient",
]
