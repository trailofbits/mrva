import collections
import dataclasses
import fnmatch
import functools
import json

from mrva import util

MRVA_CONFIG_FILENAME = "mrva-config.json"
MRVA_REPO_SARIF_FILENAME = "mrva-output.sarif"

Context = collections.namedtuple("Context", ["before", "after"])


@dataclasses.dataclass(frozen=True)
class MRVARepo:
    url: str
    download_success: bool
    mrva_name: str
    db_dir: str
    commit: str

    def mrva_dir_sarif_path(self, mrva_dir):
        return mrva_dir / self.mrva_name / MRVA_REPO_SARIF_FILENAME

    def mrva_dir_db_dir(self, mrva_dir):
        return mrva_dir / self.mrva_name / self.db_dir


@dataclasses.dataclass(frozen=True)
class MRVAConfig:
    created: int
    repos: list[MRVARepo]

    @classmethod
    def from_mrva_dir(cls, mrva_dir):
        config_path = mrva_dir / MRVA_CONFIG_FILENAME
        config_dict = json.load(config_path.open())
        repos = [MRVARepo(**r) for r in config_dict.pop("repos")]
        return cls(repos=repos, **config_dict)

    def to_mrva_dir(self, mrva_dir):
        config_path = mrva_dir / MRVA_CONFIG_FILENAME
        config_dict = dataclasses.asdict(self)
        json.dump(config_dict, config_path.open("w"), indent=4)

    def analyzable_repos(self, select=None, ignore=None):
        if select and ignore:
            raise Exception("Cannot specify 'select' and 'ignore' at the same time")

        if select is None:
            select = []
        if ignore is None:
            ignore = []

        predicate = (
            lambda r: r.download_success
            and (not select or any(term in r.mrva_name for term in select))
            and (not ignore or not any(term in r.mrva_name for term in ignore))
        )

        return util.partition(self.repos, predicate)


class SARIFLocation:
    def __init__(self, location):
        self.location = location

    @property
    def path(self):
        return self.location["artifactLocation"]["uri"]

    @property
    def artifact_index(self):
        return self.location["artifactLocation"]["index"]

    @property
    def start_line(self):
        return self.location["region"]["startLine"]

    @property
    def end_line(self):
        return self.location["region"].get("endLine", self.start_line)

    @property
    def start_column(self):
        return self.location["region"].get("startColumn", 1)

    @property
    def end_column(self):
        # This should default to the end of the line if endColumn is not
        # present. However, we do not have that information available until
        # we analyze the file contents and split it into multiple lines. TODO:
        # improve this to efficiently find the end column - use "$" for now.
        return self.location["region"].get("endColumn", "$")

    @property
    def snippet_text(self):
        # CodeQL --sarif-add-snippets provides this data
        text = self.location.get("contextRegion", {}).get("snippet", {}).get("text")

        if text is None:
            # Semgrep --sarif provides this data
            text = self.location.get("region", {}).get("snippet", {}).get("text")

        # rstrip because CodeQL includes the last line's newline for some reason
        return text.rstrip() if text is not None else text

    @property
    def snippet_start_line(self):
        # CodeQL's contextRegion begins before the matched region
        if "contextRegion" in self.location:
            return self.location["contextRegion"]["startLine"]

        # Semgrep's region snippet begins at the match itself
        return self.start_line


class SARIFResult:
    def __init__(self, result):
        self.result = result

    @property
    def rule_id(self):
        try:
            # CodeQL
            return self.result["rule"]["id"]
        except KeyError:
            # Semgrep
            return self.result["ruleId"]

    @property
    def message(self):
        return self.result["message"]["text"]

    @functools.cache
    def locations(self, flows=True):
        # Assume only CodeQL path-problem query kinds have codeFlows
        has_code_flows = "codeFlows" in self.result

        if flows and has_code_flows:
            return [
                SARIFLocation(location["location"]["physicalLocation"])
                for cf in self.result["codeFlows"]
                for tf in cf["threadFlows"]
                for location in tf["locations"]
                if "region" in location["location"]["physicalLocation"]
            ]

        return [
            SARIFLocation(location["physicalLocation"])
            for location in self.result["locations"]
            if "region" in location["physicalLocation"]
        ]


class SARIFOutput:
    def __init__(self, output):
        self.output = output

    @classmethod
    def from_path(cls, path):
        return cls(json.load(path.open()))

    @property
    def first_run(self):
        # Assume we only have a single run
        return self.output["runs"][0]

    @property
    def results(self):
        return [SARIFResult(r) for r in self.first_run["results"]]

    def artifact_contents(self, index):
        # CodeQL --sarif-add-file-contents provides this data
        return self.first_run["artifacts"][index].get("contents", {}).get("text")

    def matching_results(
        self,
        select_ids=None,
        ignore_ids=None,
        select_paths=None,
        ignore_paths=None,
    ):
        def matches_any(patterns, value):
            return any(fnmatch.fnmatchcase(value, p) for p in patterns)

        def keep(result):
            if select_ids and not matches_any(select_ids, result.rule_id):
                return False
            if ignore_ids and matches_any(ignore_ids, result.rule_id):
                return False
            if select_paths or ignore_paths:
                # For CodeQL path-problem results this is the sink;
                # otherwise the only primary location.
                path = result.locations()[-1].path
                if select_paths and not matches_any(select_paths, path):
                    return False
                if ignore_paths and matches_any(ignore_paths, path):
                    return False
            return True

        return util.partition(self.results, keep)

    def numbered_lines(self, location, context):
        contents = (
            location.snippet_text
            if location.snippet_text is not None
            else self.artifact_contents(location.artifact_index)
        )

        if contents is None:
            return []

        lines = contents.split("\n")

        if location.snippet_text is not None:
            # Assume CodeQL --sarif-add-snippets provides contextRegion, which
            # hardcodes two lines of context. In this situation output all
            # the snippet content provided.
            list_start = 0
            end = len(lines)
            line_start = location.snippet_start_line
        else:
            start = location.start_line - context.before
            end = location.end_line + context.after

            # -1 for 0-based indexing
            list_start = max(start - 1, 0)

            # 1-based indexing (line numbers)
            line_start = max(start, 1)

        return util.number_lines(lines[list_start:end], start=line_start)
