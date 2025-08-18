import dataclasses
import json

from mrva import util

MRVA_CONFIG_FILENAME = "mrva-config.json"
MRVA_REPO_SARIF_FILENAME = "mrva-output.sarif"


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
        elif ignore is None:
            ignore = []

        # fmt: off
        predicate = (
            lambda r: r.download_success and any(
                term in r.mrva_name for term in select
            ) if select
            else lambda r: r.download_success and any(
                term not in r.mrva_name for term in ignore
            ) if ignore
            else lambda r: r.download_success
        )
        # fmt: on

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


class SARIFResult:
    def __init__(self, result):
        self.result = result

    @property
    def rule_id(self):
        return self.result["rule"]["id"]

    @property
    def message(self):
        return self.result["message"]["text"]

    def locations(self, flows=True):
        # Assume only path-problem query kinds have codeFlows
        has_code_flows = "codeFlows" in self.result

        if flows and has_code_flows:
            return [
                SARIFLocation(location["location"]["physicalLocation"])
                for cf in self.result["codeFlows"]
                for tf in cf["threadFlows"]
                for location in tf["locations"]
            ]

        return [
            SARIFLocation(location["physicalLocation"])
            for location in self.result["locations"]
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

    def artifact_lines(self, result, context):
        artifact = self.first_run["artifacts"][result.artifact_index]

        # --sarif-add-file-contents provides this data
        contents = artifact.get("contents", {}).get("text", "")
        if not contents:
            return []

        lines = contents.split("\n")

        # -1 for 0-based indexing
        start = max(result.start_line - context.before - 1, 0)
        end = result.end_line + context.after

        return lines[start:end]
