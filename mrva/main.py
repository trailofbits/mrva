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


def parse_args():
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
        help="Directory to download CodeQL databases to"
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
        help="Directory containing CodeQL databases"
    )
    analyze_parser.add_argument(
        "queries",
        action="store",
        default=os.getcwd(),
        help="Queries to execute, passed to CodeQL like [<query|dir|suite|pack>...]"
    )
    filter_group = analyze_parser.add_mutually_exclusive_group(required=False)
    filter_group.add_argument(
        "--select",
        action="append",
        help="Select CodeQL databases that contain these mrva names"
    )
    filter_group.add_argument(
        "--ignore",
        action="append",
        help="Ignore CodeQL databases that contain these mrva names"
    )

    pprint_parser = subparsers.add_parser(
        "pprint",
        help="Output SARIF analysis results"
    )
    pprint_parser.add_argument(
        "mrva_sarif_file",
        type=pathlib.Path,
        help="SARIF output file from analyze"
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
    # fmt: on

    args, argv = p.parse_known_args()
    if args.command != "analyze":
        # Only analyze supports unknown arguments passed through to another command
        args = p.parse_args()
        argv = []
    else:
        argv = [a for a in argv if a != "--"]

    if args.command in ["download", "analyze"]:
        if not args.mrva_dir.is_dir():
            raise argparse.ArgumentTypeError(
                f"{args.mrva_dir} is not an existing mrva directory"
            )

    return args, argv


async def amain():
    args, argv = parse_args()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    command_dispatch = {
        "download": commands.download.main,
        "analyze": commands.analyze.main,
        "pprint": commands.pprint.main,
    }
    command = command_dispatch.get(args.command)
    if command is None:
        logger.error(f"Command unavailable: {args.command}")
        return 1

    logger.info("Starting command %s", args.command)
    result = await command(args, argv)
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
