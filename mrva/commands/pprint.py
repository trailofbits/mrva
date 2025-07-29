import collections
import itertools
import json
import logging
import textwrap

logger = logging.getLogger(__name__)

BOLD_RED = "\033[1;31m"
BOLD_GREEN = "\033[1;32m"
BOLD_CYAN = "\033[1;36m"
END = "\033[0m"

Context = collections.namedtuple("Context", ["before", "after"])


def number_lines(lines, start=0, indent=0):
    left_align = textwrap.dedent("\n".join(lines))
    numbered_lines = [
        f"{i + start} {line}" for i, line in enumerate(left_align.split("\n"))
    ]
    return textwrap.indent("\n".join(numbered_lines), " " * indent)


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
    mrva_repo_dir = args.mrva_sarif_file.parent
    mrva_dir = mrva_repo_dir.parent
    config_file = mrva_dir / "mrva-config.json"
    config = json.load(config_file.open())

    repo = next(
        (r for r in config["repos"] if r.get("mrva_name") == mrva_repo_dir.name),
        None,
    )
    if repo is None:
        logger.error(
            "Could not find config repository with name %s", mrva_repo_dir.name
        )
        return 1

    sarif_data = json.load(args.mrva_sarif_file.open())
    results = [CodeQLResult(r) for r in sarif_data["runs"][0]["results"]]
    artifacts = [CodeQLArtifact(a) for a in sarif_data["runs"][0]["artifacts"]]
    path_artifacts = {a.path: a for a in artifacts}
    path_rule_groups = {
        path_rule: list(group)
        for path_rule, group in itertools.groupby(
            sorted(results, key=lambda r: (r.path, r.rule_id)),
            key=lambda r: (r.path, r.rule_id),
        )
    }

    context = (
        Context(before=0, after=args.after_context)
        if args.after_context
        else (
            Context(before=args.before_context, after=0)
            if args.before_context
            else Context(before=args.context, after=args.context)
        )
    )
    path_results_lines = [
        (path, results, get_path_lines(path_artifacts[path], results, context))
        for (path, _), results in path_rule_groups.items()
    ]

    result_count = 0
    paths = set()
    queries = set()
    empty_line = ""
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
                repo["url"],
                repo["commit"],
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
                numbered_lines = number_lines(lines, start_line, indent=4)
                output.append(numbered_lines)
                if numbered_lines and numbered_lines[-1] != empty_line:
                    output.append(empty_line)

    print("\n".join(output))

    print("Totals")
    print(f"  * Results: {result_count}")
    print(f"  * Paths: {len(paths)}")
    print(f"  * Queries: {len(queries)}")

    return 0
