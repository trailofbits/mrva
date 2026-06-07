# mrva

`mrva` is a terminal-first approach to CodeQL [multi-repo variant analysis](https://docs.github.com/en/code-security/codeql-for-vs-code/getting-started-with-codeql-for-vs-code/running-codeql-queries-at-scale-with-multi-repository-variant-analysis). You can download existing CodeQL databases from the GitHub API, run variant analyses, and view results all from your local machine. This tool was inspired by the VSCode [CodeQL extension](https://github.com/github/vscode-codeql), but instead runs as a standalone CLI tool.

Table of contents:

- [Installing](#installing)
- [Using](#using)
- [Cloud variant analysis (`mrva run`)](#cloud-variant-analysis-mrva-run)
- [Developing](#developing)
  - [Testing](#testing)
  - [Linting](#linting)

## Installing

First, install `mrva` from [PyPI](https://pypi.org/project/mrva/):

```bash
$ python -m pip install mrva
$ mrva -h
```

_Or, use your favorite Python package installer like `pipx` or `uv`._

## Using

`mrva` has the following command tree:

- `mrva`
  - `download`
    - `top`
    - `org`
    - `repo`
    - `query`
    - `from-file`
  - `analyze`
  - `pprint`
  - `print-ast` (experimental)
  - `run` (cloud)
    - `top`
    - `org`
    - `repo`
    - `query`
    - `from-file`

Using `mrva` generally requires three steps:

1. Downloading existing CodeQL databases from the GitHub API
1. Running CodeQL variant analyses against these databases
1. Viewing the results

First, ensure you have a `codeql` binary in your `$PATH` (releases [here](https://github.com/github/codeql-cli-binaries/releases)).

Next, create a directory to store `mrva` data:

```bash
$ mkdir dbs/
```

This directory will eventually contain CodeQL databases, tool configuration, SARIF results, and other information `mrva` needs to operate.

Use the `mrva download` command to download CodeQL databases:

```bash
$ mrva download --token $GITHUB_TOKEN --language ruby dbs/ top --limit 100
```

<!-- prettier-ignore -->
> [!NOTE]
> `download` will automatically use the `$GITHUB_TOKEN` environment variable if it's available.

This command will download CodeQL databases of the top 100 GitHub Ruby projects (by star count). You can download other databases by specifying a different `--language`, or using a different download strategy like `download org` or `download repo`.

Use the `mrva analyze` command to analyze the downloaded databases:

```bash
$ mrva analyze dbs/ /path/to/queries -- --rerun --threads=0
```

Any flags included after `--` are passed directly to the CodeQL binary.

<!-- prettier-ignore -->
> [!NOTE]
> `mrva` recommends using the `--threads` flag to process multiple queries within a _single_ CodeQL analysis instead of parallelizing multiple CodeQL analyses. This prevents contention between `mrva` and CodeQL.

Use the `mrva pprint` command to view analysis results:

```bash
$ mrva pprint dbs/
```

You can also use the `pprint` command to print raw CodeQL SARIF results:

```bash
$ codeql database analyze \
    --format sarif-latest \
    --sarif-add-file-contents \
    --output output.sarif \
    -- db/ query.ql
$ mrva pprint output.sarif
```

Many of these commands take additional flags to modify their functionality. For example, `analyze` and `pprint` take `--select` and `--ignore` flags to filter repositories. Use the `--help` flag to explore all functionality provided by a given command.

## Cloud variant analysis (`mrva run`)

`mrva run` dispatches a CodeQL query as a cloud job via GitHub Actions, polls for results, and downloads per-repo SARIF into the same directory layout as the local workflow — so `mrva pprint` works unchanged.

### Prerequisites

- A **controller repository** on GitHub (can be empty, but must have at least one commit). Set it via `--controller-repo owner/repo` or the `$MRVA_CONTROLLER_REPO` environment variable.
- A GitHub token with `repo` scope (`$GITHUB_TOKEN`).
- A `codeql` binary in your `$PATH` (used to bundle the query pack before submission).

### Usage

```bash
# Run against the top 100 Python repos (by star count)
$ mrva run --language python --controller-repo owner/ctrl results/ query.ql top --limit 100

# Run against all repos in an organization
$ mrva run --language java --controller-repo owner/ctrl results/ query.ql org --owner my-org

# Run against a single repo
$ mrva run --language python --controller-repo owner/ctrl results/ query.ql repo --owner octocat --repository hello-world

# Run against repos matching a search query
$ mrva run --language go --controller-repo owner/ctrl results/ query.ql query -q "org:golang stars:>100"

# Run against a custom repo list file
$ mrva run --language python --controller-repo owner/ctrl results/ query.ql from-file repos.json
```

<!-- prettier-ignore -->
> [!NOTE]
> `run` will automatically use `$GITHUB_TOKEN` and `$MRVA_CONTROLLER_REPO` if they are set.

The command blocks and polls until the cloud job finishes, downloading each repo's SARIF as it completes. Results land in `results/mrva-{language}-{owner}-{repo}/mrva-output.sarif`.

### Resuming after interruption

If the process is killed during polling, the variant analysis ID is persisted to `results/mrva-cloud-state.json` immediately after submission. Resume with:

```bash
$ mrva run --resume <variant_analysis_id> results/
```

## Developing

`mrva` uses [`poetry`](https://python-poetry.org/) for dependency and configuration management.

Before proceeding, install project dependencies with the following command:

```bash
$ poetry install --with dev
```

<!-- prettier-ignore -->
> [!NOTE]
> When running `mrva analyze` in the Poetry environment you may need to pass `--` to `poetry run` like `poetry run -- mrva analyze`. This prevents Poetry from getting confused about which arguments are its arguments, `mrva`'s arguments, and `codeql`'s arguments.

### Linting

Lint all project files with the following command:

```bash
$ poetry run pre-commit run --all-files
```

### Testing

Run Python tests with the following command:

```bash
$ poetry run pytest --cov
```
