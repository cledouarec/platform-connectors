# Contribution guidelines

First off, thank you for considering contributing to rate-my-project.

If your contribution is not straightforward, please first discuss the change you
wish to make by creating a new issue before making the change.

## Reporting issues

Before reporting an issue on the
[issue tracker](https://github.com/cledouarec/rate-my-project/issues),
please check that it has not already been reported by searching for some related
keywords.

## Pull requests

Try to do one pull request per change.

## Commit Message Format

*This specification is inspired by and supersedes the [AngularJS commit message format][commit-message-format].*

We have very precise rules over how our Git commit messages must be formatted.
This format leads to **easier to read commit history**.

The commit message must respect the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard.

To facilitate its usage, we use [commitizen](https://commitizen-tools.github.io/commitizen/).

Each commit message consists of a **header**, a **body**, and a **footer**.

```
<header>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

The `header` is mandatory and must conform to the [Commit Message Header](#commit-header) format.

The `body` is preferred for all commits except for those of type "docs".

The `footer` is optional. The [Commit Message Footer](#commit-footer) format describes what the footer is used for and the structure it must have.

### Commit Message Header

```
<type>(<scope>): <short summary>
  │       │             │
  │       │             └─⫸ Summary in present tense. Not capitalized. No period at the end.
  │       │
  │       └─⫸ Commit Scope: connectors|config|dashboard|metrics|template
  │
  └─⫸ Commit Type: build|ci|docs|feat|fix|perf|refactor|test
```

The `<type>` and `<summary>` fields are mandatory, the `(<scope>)` field is optional.


#### Type

Must be one of the following:

* **build**: Changes that affect the build system or external dependencies (example scopes: gulp, broccoli, npm)
* **ci**: Changes to our CI configuration files and scripts (examples: CircleCi, SauceLabs)
* **docs**: Documentation only changes
* **feat**: A new feature
* **fix**: A bug fix
* **perf**: A code change that improves performance
* **refactor**: A code change that neither fixes a bug nor adds a feature
* **test**: Adding missing tests or correcting existing tests

### Updating the changelog

There is no need to update [CHANGELOG](https://github.com/cledouarec/rate-my-project/blob/main/CHANGELOG.md) file.

The changelog is updated automatically by the github action.

## Developing

### Set up

It is recommended to use a virtual environment :
```shell
python -m venv venv
```
To install the module and the main script, simply do :
```
pip install .
```
It is useful to install extra tools.
These tools can be installed with the following command :
```
pip install '.[dev]'
```
The Git hooks can be installed with :
```
pre-commit install
```
The hooks can be run manually at any time :
```
pre-commit run --all-file
```
