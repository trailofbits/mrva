# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support for pprint'ing Semgrep SARIF results
- `pprint` CLI flags for filtering result output: `--{select,ignore}-{id,path}`

### Changed

- Suppress `BrokenPipeError` exceptions in `pprint` when piping output (e.g. to `less`)

## [0.5.0] - 2024-12-11

### Added

- Initial release of `mrva`
- `mrva download` command for downloading CodeQL databases
- `mrva analyze` command for analyzing many databases and aggregating results
- `mrva pprint` command for printing analyze results
- `mrva pprint` command for printing standard CodeQL SARIF results
- `mrva print-ast` command for printing code AST information (experimental)
