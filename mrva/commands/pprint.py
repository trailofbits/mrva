import collections
import logging
import sys

import jinja2

from mrva import types
from mrva import util

logger = logging.getLogger(__name__)

BOLD_RED = "\033[1;31m"
BOLD_GREEN = "\033[1;32m"
BOLD_CYAN = "\033[1;36m"
END = "\033[0m"

Context = collections.namedtuple("Context", ["before", "after"])

OUTPUT_TEMPLATE = """
{% for tr in trs %}
{{ tr["rule_id"] }}: {{ tr["message"] }}

{% for loc in tr["locations"] %}
  {{ loc["path"] }} (ln: {{ loc["start_line"] }}:{{ loc["end_line"] }} col: {{ loc["start_column"] }}:{{ loc["end_column"] }})
  {{ loc["link"] }}

  {% for line_no, line in loc["lines"] %}
  {{ line_no }} {{ line }}
  {% endfor %}

{% endfor %}
{% endfor %}
""".strip()

ENVIRONMENT = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
TEMPLATE = ENVIRONMENT.from_string(OUTPUT_TEMPLATE)


def permalink(url, commit, path, start_line, end_line):
    # This may eventually need to be adjusted or configurable. A short hash
    # may not uniquely identify a commit in repos with many commits.
    # https://github.com/desktop/desktop/issues/6662
    hash_size = 8

    return f"{url}/blob/{commit[:hash_size]}/{path}#L{start_line}-L{end_line}"


def color(color, s):
    return f"{color}{s}{END}"


def print_sarif_output(repo, sarif_path, context, flows=True, file=None):
    if file is None:
        # https://github.com/pytest-dev/pytest/issues/5997
        file = sys.stdout

    sarif_output = types.SARIFOutput.from_path(sarif_path)
    trs = [
        {
            "rule_id": color(BOLD_RED, result.rule_id),
            "message": color(BOLD_CYAN, result.message),
            "locations": [
                {
                    "path": color(BOLD_GREEN, location.path),
                    "start_line": location.start_line,
                    "end_line": location.end_line,
                    "start_column": location.start_column,
                    "end_column": location.end_column,
                    "link": permalink(
                        repo.url,
                        repo.commit,
                        location.path,
                        location.start_line,
                        location.end_line,
                    ),
                    "lines": util.number_lines(
                        sarif_output.artifact_lines(location, context),
                        # 1-based indexing (line numbers)
                        start=max(location.start_line - context.before, 1),
                    ),
                }
                for location in result.locations(flows=flows)
            ],
        }
        for result in sarif_output.results
    ]
    if trs:
        print(TEMPLATE.render(trs=trs), file=file)


async def main(args, argv):
    config = types.MRVAConfig.from_mrva_dir(args.mrva_dir)
    logger.info("pprinting mrva directory created at %s", config.created)

    kept, discarded = config.analyzable_repos(args.select, args.ignore)
    logger.info(
        "Found %d analyzable repositories, discarded %d", len(kept), len(discarded)
    )

    context = (
        Context(before=0, after=args.after_context)
        if args.after_context
        else (
            Context(before=args.before_context, after=0)
            if args.before_context
            else Context(before=args.context, after=args.context)
        )
    )

    repo_sarif_paths = [
        (repo, repo.mrva_dir_sarif_path(args.mrva_dir)) for repo in kept
    ]
    for repo, sarif_path in repo_sarif_paths:
        if sarif_path.exists():
            print_sarif_output(repo, sarif_path, context, flows=args.flows)
        else:
            logger.warning("Skipping %s, could not find SARIF output", repo.mrva_name)

    return 0
