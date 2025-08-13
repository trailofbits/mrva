import collections
import json
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
    return f"{url}/blob/{commit[:7]}/{path}#L{start_line}-L{end_line}"


def color(color, s):
    return f"{color}{s}{END}"


class CodeQLResult:
    def __init__(self, result):
        self.result = result

    @property
    def rule_id(self):
        return self.result["ruleId"]

    @property
    def message(self):
        return self.result["message"]["text"]

    @property
    def physical_location(self):
        return self.result["locations"][0]["physicalLocation"]

    @property
    def path(self):
        return self.physical_location["artifactLocation"]["uri"]

    @property
    def start_line(self):
        return self.physical_location["region"]["startLine"]

    @property
    def end_line(self):
        return self.physical_location["region"].get("endLine", self.start_line)


class CodeQLArtifact:
    def __init__(self, artifact):
        self.artifact = artifact

    @property
    def path(self):
        return self.artifact["location"]["uri"]

    @property
    def contents(self):
        # --sarif-add-file-contents provides this data
        return self.artifact.get("contents", {}).get("text", "")


def get_path_lines(artifact, results, context):
    if not artifact.contents:
        return [[]] * len(results)

    def line_slice(start, end):
        # -1 for 0-based indexing
        return slice(max(start - context.before - 1, 0), end + context.after)

    lines = artifact.contents.split("\n")

    return (lines[line_slice(result.start_line, result.end_line)] for result in results)


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

    def exists_or_log(repo_path):
        exists = repo_path[1].exists()
        if not exists:
            logger.warning(
                "Skipping %s, could not find SARIF output", repo_path[0].mrva_name
            )
        return exists

    existing_repo_paths, _ = util.partition(repo_sarif_paths, exists_or_log)

    for repo, path in existing_repo_paths:
        sarif_data = json.load(path.open())
        results = [CodeQLResult(r) for r in sarif_data["runs"][0]["results"]]
        artifacts = [CodeQLArtifact(a) for a in sarif_data["runs"][0]["artifacts"]]
        path_artifacts = {a.path: a for a in artifacts}
        path_rule_groups = {
            path_rule: list(group)
            for path_rule, group in util.sorted_groupby(
                results, lambda r: (r.path, r.rule_id)
            )
        }
        path_results_lines = [
            (path, results, get_path_lines(path_artifacts[path], results, context))
            for (path, _), results in path_rule_groups.items()
        ]

        output = []
        for path, results, lines in path_results_lines:
            paths.add(path)
            result_count += len(results)
            output.append(color(BOLD_RED, path))
            output.append(empty_line)

            for result, lines in zip(results, lines, strict=True):
                queries.add(result.rule_id)
                name = color(BOLD_CYAN, result.rule_id)
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

                if lines:
                    start_line = max(result.start_line - context.before, 1)
                    numbered_lines = util.number_lines(lines, start_line, indent=4)
                    output.append(numbered_lines)
                    if numbered_lines and numbered_lines[-1] != empty_line:
                        output.append(empty_line)

        print("\n".join(output))

    print("Totals")
    print(f"  * Results: {result_count}")
    print(f"  * Paths: {len(paths)}")
    print(f"  * Queries: {len(queries)}")

    return 0
