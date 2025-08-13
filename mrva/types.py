import dataclasses
import json

from mrva import util

MRVA_CONFIG_FILENAME = "mrva-config.json"
MRVA_REPO_SARIF_FILENAME = "mrva-output.sarif"


@dataclasses.dataclass(frozen=True, kw_only=True)
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


@dataclasses.dataclass(frozen=True, kw_only=True)
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


class SARIFResult:
    def __init__(self, result):
        self.result = result

    @property
    def rule_id(self):
        return self.result["rule"]["id"]

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
    def artifact_index(self):
        return self.physical_location["artifactLocation"]["index"]

    @property
    def start_line(self):
        return self.physical_location["region"]["startLine"]

    @property
    def end_line(self):
        return self.physical_location["region"].get("endLine", self.start_line)


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
        for r in self.first_run["results"]:
            yield SARIFResult(r)

    def result_lines(self, result, context):
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
