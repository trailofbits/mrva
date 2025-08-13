import collections
import logging

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

    empty_line = ""
    result_count = 0
    paths = set()
    queries = set()

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

    for repo, sarif_path in existing_repo_paths:
        sarif_output = types.SARIFOutput.from_path(sarif_path)
        path_rule_groups = {
            path_rule: list(group)
            for path_rule, group in util.sorted_groupby(
                sarif_output.results, lambda r: (r.path, r.rule_id)
            )
        }

        output = []
        for (path, rule_id), results in path_rule_groups.items():
            paths.add(path)
            result_count += len(results)
            output.append(color(BOLD_RED, path))
            output.append(empty_line)

            for result in results:
                queries.add(rule_id)
                name = color(BOLD_CYAN, rule_id)
                description = color(BOLD_GREEN, result.message)
                line_range = f"(ln: {result.start_line}-{result.end_line})"
                link = permalink(
                    repo.url,
                    repo.commit,
                    path,
                    result.start_line,
                    result.end_line,
                )
                header = f"{name}: {description} {line_range}"

                output.append("  " + header)
                output.append("  " + link)
                output.append(empty_line)

                lines = sarif_output.result_lines(result, context)
                if lines:
                    # 1-based indexing
                    start_line = max(result.start_line - context.before, 1)
                    numbered_lines = util.number_lines(lines, start_line, indent=4)
                    output.append(numbered_lines)
                    if numbered_lines and numbered_lines[-1] != empty_line:
                        output.append(empty_line)

        if output:
            print("\n".join(output))

    print("Totals")
    print(f"  * Results: {result_count}")
    print(f"  * Paths: {len(paths)}")
    print(f"  * Queries: {len(queries)}")

    return 0
