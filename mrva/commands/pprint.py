import collections
import logging

import jinja2

from mrva import types
from mrva import util

logger = logging.getLogger(__name__)

BOLD_RED = "\033[1;31m"
BOLD_GREEN = "\033[1;32m"
BOLD_CYAN = "\033[1;36m"
END = "\033[0m"

Context = collections.namedtuple("Context", ["before", "after"])


def permalink(url, commit, path, start_line, end_line):
    # This may eventually need to be adjusted or configurable. A short hash
    # may not uniquely identify a commit in repos with many commits.
    # https://github.com/desktop/desktop/issues/6662
    hash_size = 8

    return f"{url}/blob/{commit[:hash_size]}/{path}#L{start_line}-L{end_line}"


def color(color, s):
    return f"{color}{s}{END}"


NO_FLOW_TEMPLATE = """
{% for tr in trs %}
{{ tr["rule_id"] }}

{% for r in tr["results"] %}
  {{ r["message"] }}: {{ r["path"] }} (ln: {{ r["start_line"] }}-{{ r["end_line"] }})
  {{ r["link"] }}

  {% for line_no, line in r["lines"] %}
    {{ line_no }} {{ line }}
  {% endfor %}

{% endfor %}
{% endfor %}
""".strip()


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

    def exists_or_log(repo_sarif_path):
        exists = repo_sarif_path[1].exists()
        if not exists:
            logger.warning(
                "Skipping %s, could not find SARIF output",
                repo_sarif_path[0].mrva_name,
            )
        return exists

    existing_repo_paths, _ = util.partition(repo_sarif_paths, exists_or_log)
    environment = jinja2.Environment(trim_blocks=True)

    for repo, sarif_path in existing_repo_paths:
        sarif_output = types.SARIFOutput.from_path(sarif_path)
        rule_groups = {
            rule_id: list(group)
            for rule_id, group in util.sorted_groupby(
                sarif_output.results, lambda r: r.rule_id
            )
        }

        trs = [
            {
                "rule_id": color(BOLD_RED, rule_id),
                "results": [
                    {
                        "message": color(BOLD_CYAN, result.message),
                        "path": color(BOLD_GREEN, result.path),
                        "start_line": result.start_line,
                        "end_line": result.end_line,
                        "link": permalink(
                            repo.url,
                            repo.commit,
                            result.path,
                            result.start_line,
                            result.end_line,
                        ),
                        "lines": util.number_lines(
                            sarif_output.result_lines(result, context),
                            # 1-based indexing
                            start=max(result.start_line - context.before, 1),
                        ),
                    }
                    for result in results
                ],
            }
            for rule_id, results in rule_groups.items()
        ]

        if trs:
            template = environment.from_string(NO_FLOW_TEMPLATE)
            print(template.render(trs=trs))

    return 0
