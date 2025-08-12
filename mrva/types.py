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
