# mrva

`mrva` is a CLI tool for running local CodeQL [multi-repo variant analysis](https://docs.github.com/en/code-security/codeql-for-vs-code/getting-started-with-codeql-for-vs-code/running-codeql-queries-at-scale-with-multi-repository-variant-analysis). You can download existing CodeQL databases from the GitHub API, run variant analyses, and view results all from your local machine. This tool was inspired by the VSCode [CodeQL extension](https://github.com/github/vscode-codeql), but instead runs as a standalone CLI tool.

Table of contents:

- [Installing](#installing)
- [Using](#using)
- [Developing](#developing)
  - [Testing](#testing)
  - [Linting](#linting)

## Installing

Currently `mrva` must be installed from the git source. If/when it is open sourced we will upload it to PyPI.

To install:

```bash
$ git clone https://github.com/trailofbits/mrva.git
$ python -m pip install mrva/
$ mrva -h
```

## Using

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

To download CodeQL databases use the `mrva download` command:

```bash
$ mrva download --token $GITHUB_TOKEN --language ruby dbs/ top --limit 100
```

This command will download CodeQL databases of the top 100 GitHub Ruby projects (by star count). You can download other databases by specifying a different `--language`, or using a different search strategy like `download org` or `download repo`.

Once you have your desired databases you can run CodeQL analyses against them using the `mrva analyze` command:

```bash
$ mrva analyze dbs/ /path/to/queries -- --rerun --threads=0
```

Any flags included after `--` are passed directly to the CodeQL binary.

<!-- prettier-ignore -->
> [!NOTE]
> `mrva` recommends using the `--threads` flag to process multiple queries within a _single_ CodeQL analysis instead of parallelizing multiple CodeQL analyses. This prevents `mrva` from competing with CodeQL for parallel processing.

After this analysis is done you can view the results using the `mrva pprint` command:

```bash
$ mrva pprint dbs/
```

Many of these commands take additional flags to modify their functionality. For example, `analyze` and `pprint` take `--select` and `--ignore` flags to filter repositories. Use the `--help` flag to explore all functionality provided by a given command.

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
