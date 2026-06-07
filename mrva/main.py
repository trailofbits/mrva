import argparse
import asyncio
import logging
import os
import pathlib
import sys

from mrva import __version__
from mrva import commands

logger = logging.getLogger(__name__)


# https://codeql.github.com/docs/codeql-overview/supported-languages-and-frameworks/
# https://github.com/github-linguist/linguist/blob/main/lib/linguist/languages.yml
CODEQL_LANGUAGES = [
    "c",
    "cpp",
    "csharp",
    "go",
    "golang",
    "java",
    "kotlin",
    "javascript",
    "js",
    "typescript",
    "ts",
    "python",
    "ruby",
    "rust",
    "swift",
]


class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if envvar and envvar in os.environ:
            default = os.environ[envvar]
        if required and default:
            required = False

        super(EnvDefault, self).__init__(
            default=default,
            required=required,
            **kwargs,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


def parse_args(args):
    # fmt: off
    p = argparse.ArgumentParser(
        description="A CLI for CodeQL multi-repo variant analysis",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Set logging level to debug",
    )
    p.add_argument(
        "-V",
        "--version",
        action="version",
        version=__version__,
    )

    subparsers = p.add_subparsers(dest="command", help="Command help")

    download_parser = subparsers.add_parser(
        "download",
        help="Download existing CodeQL database from the GitHub API",
    )
    download_parser.add_argument(
        "-t",
        "--token",
        action=EnvDefault,
        envvar="GITHUB_TOKEN",
        help="GitHub API token, or specify $GITHUB_TOKEN"
    )
    download_parser.add_argument(
        "-b",
        "--base-url",
        action=EnvDefault,
        default="https://api.github.com",
        envvar="GITHUB_BASE_URL",
        help="GitHub base URL, or specify $GITHUB_BASE_URL"
    )
    download_parser.add_argument(
        "--timeout",
        action="store",
        default=30,
        help="HTTP request timeout"
    )
    download_parser.add_argument(
        "-l",
        "--language",
        action="store",
        required=True,
        choices=CODEQL_LANGUAGES,
        help="CodeQL database language"
    )
    download_parser.add_argument(
        "mrva_dir",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="mrva storage and configuration directory"
    )

    download_subparsers = download_parser.add_subparsers(
        dest="download_command",
        help="Download command help",
    )

    top_parser = download_subparsers.add_parser(
        "top",
        help="Top repositories by star count",
    )
    top_parser.add_argument(
        "-i",
        "--limit",
        action="store",
        choices=[10, 100, 1000],
        default=100,
        type=int,
        help="Maximum number of repositories"
    )

    org_parser = download_subparsers.add_parser(
        "org",
        help="Repositories for a specific organization",
    )
    org_parser.add_argument(
        "-o",
        "--owner",
        action="store",
        help="GitHub repository owner"
    )
    org_parser.add_argument(
        "-i",
        "--limit",
        action="store",
        choices=[10, 100, 1000],
        default=0,
        type=int,
        help="Maximum number of repositories"
    )

    repo_parser = download_subparsers.add_parser(
        "repo",
        help="Specific repository"
    )
    repo_parser.add_argument(
        "-o",
        "--owner",
        action="store",
        help="GitHub repository owner"
    )
    repo_parser.add_argument(
        "-r",
        "--repository",
        action="store",
        help="GitHub repository name"
    )

    from_file_parser = download_subparsers.add_parser(
        "from-file",
        help="Custom repository list"
    )
    from_file_parser.add_argument(
        "json_file",
        action="store",
        type=argparse.FileType("r"),
        help="File containing repository information"
    )

    query_parser = download_subparsers.add_parser(
        "query",
        help="Repositories based on an arbitrary search query",
    )
    query_parser.add_argument(
        "-i",
        "--limit",
        action="store",
        choices=[10, 100, 1000],
        default=100,
        type=int,
        help="Maximum number of repositories"
    )
    query_parser.add_argument(
        "-q",
        "--query",
        action="store",
        help="GitHub repository search query"
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run CodeQL analyses against downloaded databases"
    )
    analyze_parser.add_argument(
        "mrva_dir",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="mrva storage and configuration directory"
    )
    analyze_parser.add_argument(
        "queries",
        action="store",
        default=os.getcwd(),
        help="Queries to execute, passed to CodeQL like [<query|dir|suite|pack>...]"
    )
    analyze_filter_group = analyze_parser.add_mutually_exclusive_group(required=False)
    analyze_filter_group.add_argument(
        "--select",
        action="append",
        help="Select CodeQL databases that contain these mrva names"
    )
    analyze_filter_group.add_argument(
        "--ignore",
        action="append",
        help="Ignore CodeQL databases that contain these mrva names"
    )

    pprint_parser = subparsers.add_parser(
        "pprint",
        help="Output SARIF analysis results"
    )
    pprint_parser.add_argument(
        "target",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="mrva storage and configuration directory, or CodeQL SARIF file"
    )
    pprint_parser.add_argument(
        "--repo-url",
        action="store",
        help="GitHub repo URL, like https://github.com/<org>/<repo>/blob/<commit>",
    )
    pprint_parser.add_argument(
        "--no-flows",
        dest="flows",
        action="store_false",
        help="Disable printing code flows",
    )
    pprint_filter_group = pprint_parser.add_mutually_exclusive_group(required=False)
    pprint_filter_group.add_argument(
        "--select",
        action="append",
        help="Select CodeQL SARIF results that contain these mrva names"
    )
    pprint_filter_group.add_argument(
        "--ignore",
        action="append",
        help="Ignore CodeQL SARIF results that contain these mrva names"
    )
    context_group = pprint_parser.add_mutually_exclusive_group(required=False)
    context_group.add_argument(
        "-A",
        "--after-context",
        type=int,
        help="Print N lines of trailing context after each match"
    )
    context_group.add_argument(
        "-B",
        "--before-context",
        type=int,
        help="Print N lines of leading context before each match"
    )
    context_group.add_argument(
        "-C",
        "--context",
        type=int,
        default=1,
        help="Print N lines of leading and trailing context surrounding each match"
    )

    print_ast_parser = subparsers.add_parser(
        "print-ast",
        help="Print AST information for source code files in CodeQL databases"
    )
    print_ast_parser.add_argument(
        "mrva_dir",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="mrva storage and configuration directory"
    )
    print_ast_parser.add_argument(
        "-l",
        "--language",
        action="store",
        required=True,
        choices=CODEQL_LANGUAGES,
        help="CodeQL database language"
    )
    print_ast_parser.add_argument(
        "-m",
        "--match",
        action="store",
        default="%",
        help="Select filenames that match this pattern, uses SQL LIKE syntax"
    )
    print_ast_filter_group = print_ast_parser.add_mutually_exclusive_group(required=False)
    print_ast_filter_group.add_argument(
        "--select",
        action="append",
        help="Select CodeQL SARIF results that contain these mrva names"
    )
    print_ast_filter_group.add_argument(
        "--ignore",
        action="append",
        help="Ignore CodeQL SARIF results that contain these mrva names"
    )
    run_parser = subparsers.add_parser(
        "run",
        help="Run a CodeQL variant analysis as a cloud job via GitHub Actions",
    )
    run_parser.add_argument(
        "-t",
        "--token",
        action=EnvDefault,
        envvar="GITHUB_TOKEN",
        help="GitHub API token, or specify $GITHUB_TOKEN",
    )
    run_parser.add_argument(
        "-b",
        "--base-url",
        action=EnvDefault,
        default="https://api.github.com",
        envvar="GITHUB_BASE_URL",
        help="GitHub base URL, or specify $GITHUB_BASE_URL",
    )
    run_parser.add_argument(
        "--timeout",
        action="store",
        default=30,
        help="HTTP request timeout",
    )
    run_parser.add_argument(
        "-c",
        "--controller-repo",
        action=EnvDefault,
        envvar="MRVA_CONTROLLER_REPO",
        required=False,
        help="Controller repository (owner/repo), or specify $MRVA_CONTROLLER_REPO",
    )
    run_parser.add_argument(
        "-l",
        "--language",
        action="store",
        choices=CODEQL_LANGUAGES,
        help="CodeQL query language",
    )
    run_parser.add_argument(
        "--resume",
        action="store",
        type=int,
        default=None,
        metavar="VARIANT_ANALYSIS_ID",
        help="Resume a previously submitted variant analysis by ID",
    )
    run_parser.add_argument(
        "mrva_dir",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="mrva storage and configuration directory",
    )
    run_parser.add_argument(
        "query",
        action="store",
        nargs="?",
        help="Path to a .ql file or qlpack directory",
    )

    run_subparsers = run_parser.add_subparsers(
        dest="run_command",
        help="Repository selection strategy",
    )

    run_top_parser = run_subparsers.add_parser(
        "top",
        help="Top repositories by star count",
    )
    run_top_parser.add_argument(
        "-i",
        "--limit",
        action="store",
        choices=[10, 100, 1000],
        default=100,
        type=int,
        help="Maximum number of repositories",
    )

    run_org_parser = run_subparsers.add_parser(
        "org",
        help="Repositories for a specific organization",
    )
    run_org_parser.add_argument(
        "-o",
        "--owner",
        action="store",
        required=True,
        help="GitHub organization name",
    )

    run_repo_parser = run_subparsers.add_parser(
        "repo",
        help="Specific repository",
    )
    run_repo_parser.add_argument(
        "-o",
        "--owner",
        action="store",
        required=True,
        help="GitHub repository owner",
    )
    run_repo_parser.add_argument(
        "-r",
        "--repository",
        action="store",
        required=True,
        help="GitHub repository name",
    )

    run_query_parser = run_subparsers.add_parser(
        "query",
        help="Repositories based on an arbitrary search query",
    )
    run_query_parser.add_argument(
        "-i",
        "--limit",
        action="store",
        choices=[10, 100, 1000],
        default=100,
        type=int,
        help="Maximum number of repositories",
    )
    run_query_parser.add_argument(
        "-q",
        "--query",
        action="store",
        required=True,
        help="GitHub repository search query",
    )

    run_from_file_parser = run_subparsers.add_parser(
        "from-file",
        help="Custom repository list",
    )
    run_from_file_parser.add_argument(
        "json_file",
        action="store",
        type=argparse.FileType("r"),
        help="File containing repository information",
    )

    # fmt: on

    known, unknown = p.parse_known_args(args=args)
    if known.command == "analyze":
        # Only analyze supports unknown arguments passed through to another command
        unknown = [a for a in unknown if a != "--"]
    else:
        known = p.parse_args(args=args)
        unknown = []

    if known.command in ["download", "analyze", "print-ast", "run"]:
        if not known.mrva_dir.is_dir():
            raise argparse.ArgumentTypeError(
                f"{known.mrva_dir} is not an existing mrva directory"
            )
    if known.command == "run" and not known.resume and not known.language:
        p.error("--language is required for mrva run unless --resume is specified")
    elif known.command == "pprint":
        if not (known.target.is_dir() or known.target.is_file()):
            raise argparse.ArgumentTypeError(
                f"{known.target} is not an existing mrva directory or SARIF file"
            )

    return known, unknown


async def amain():
    args, argv = parse_args(sys.argv[1:])

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    command_dispatch = {
        "download": commands.download.main,
        "analyze": commands.analyze.main,
        "pprint": commands.pprint.main,
        "print-ast": commands.print_ast.main,
        "run": commands.run.main,
    }
    command = command_dispatch.get(args.command)
    if command is None:
        logger.error(f"Command unavailable: {args.command}")
        return 1

    logger.info("Starting command %s", args.command)
    try:
        result = await command(args, argv)
    except FileNotFoundError as e:
        if e.filename == "codeql":
            logger.error(
                "Could not find 'codeql' binary on your PATH, add it and try again"
            )
            return 1
        else:
            raise
    logger.info("Finished command %s", args.command)

    return result


def main():
    try:
        return asyncio.run(amain())
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, exiting...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
