import collections
import itertools
import json
import logging
import textwrap

logger = logging.getLogger(__name__)

BOLD_RED = "\033[1;31m"
BOLD_GREEN = "\033[1;32m"
END = "\033[0m"

Context = collections.namedtuple("Context", ["before", "after"])


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
        return self.artifact["contents"]["text"]


def get_path_lines(artifact, results, context):
    if not artifact:
        return ""

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

    code_dir = mrva_repo_dir / repo["code_dir"]
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

    empty_line = ""
    output = []
    for path, results, lines in path_results_lines:
        output.append(color(BOLD_RED, code_dir / path))
        output.append(empty_line)

        for result, result_lines in zip(results, lines, strict=True):
            numbered_lines = [
                f"{i + max(result.start_line - context.before, 1)} {line}"
                for i, line in enumerate(result_lines)
            ]
            result_name = color(BOLD_GREEN, result.rule_id)
            result_description = color(BOLD_GREEN, result.message)
            result_line_range = f"{result.start_line}-{result.end_line}"
            result_header = f"{' ' * 2}{result_name}: {result_description} (ln: {result_line_range})"
            result_joined_lines = textwrap.indent(
                textwrap.dedent("\n".join(numbered_lines)), " " * 4
            )

            output.append(result_header)
            output.append(empty_line)
            output.append(result_joined_lines)
            if numbered_lines and numbered_lines[-1] != empty_line:
                output.append(empty_line)

    print("\n".join(output))

    return 0
