# Platform connectors

**Table of Contents**
- [Platform connectors](#platform-connectors)
  - [Overview](#overview)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Contribution](#contribution)

## Overview

This module provides async client classes to interact with:
- Jira: fetch issues and metadata
- Confluence: retrieve pages and space information
- GitLab: access repositories and merge requests
- Http: base HTTP client for platform communication

All clients require authentication credentials passed as constructor parameters.

## Installation

All the project is managed with **Poetry**. To install it, please visit the
[official page](https://python-poetry.org/docs/#installation) and follow these
instructions :
```shell
poetry shell
poetry install --without dev
```

For the developers, it is useful to install extra tools like :
* [commitizen](https://commitizen-tools.github.io/commitizen/)
* [pre-commit](https://pre-commit.com)
* [pytest](http://docs.pytest.org)
* [ruff](https://docs.astral.sh/ruff/)

These tools can be installed with the following command :
```shell
poetry install
```
The Git hooks can be installed with :
```shell
poetry run pre-commit install
```
The hooks can be run manually at any time :
```shell
poetry run pre-commit run --all-file
```

## Usage

```python
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
        space = await confluence_session.get_space_from_key(space_key="DOCS")
        pages = await confluence_session.get_all_pages_in_space(space_id=space["id"])

asyncio.run(main())
```
## Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in the work by you, shall be as defined in the Apache-2.0 license
without any additional terms or conditions.

See [CONTRIBUTING.md](CONTRIBUTING.md).