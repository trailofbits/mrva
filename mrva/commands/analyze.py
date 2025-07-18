import json
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


async def main(args, argv):
    config_path = args.mrva_dir / "mrva-config.json"
    config = json.load(config_path.open())
    logger.info("Analyzing mrva directory created at %s", config["created"])

    analyzable_repos = [r for r in config["repos"] if r["success"]]
    logger.info("Analyzing %d repositories", len(analyzable_repos))

    total_results = 0
    for repo in analyzable_repos:
        output_path = args.mrva_dir / repo["mrva_name"] / "mrva-output.sarif"
        db_dir = args.mrva_dir / repo["mrva_name"] / repo["db_dir"]
        command = [
            "codeql",
            "database",
            "analyze",
            "--format",
            "sarif-latest",
            "--output",
            output_path,
            *argv,
            "--",
            str(db_dir),
            args.queries,
        ]

        try:
            process = subprocess.run(
                command,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        except FileNotFoundError:
            logger.error(
                "Could not find 'codeql' binary on your PATH, add it and try again"
            )
            return 1

        if process.returncode != 0:
            logger.warning(
                "CodeQL analysis failed for %s returncode %d",
                repo["mrva_name"],
                process.returncode,
            )
            continue

        output = json.load(output_path.open())
        repo_result_count = len(output["runs"][0]["results"])
        total_results += repo_result_count
        logger.info("Found %d results for %s", repo_result_count, repo["mrva_name"])

    logger.info("Found %d total results for %s", total_results, args.mrva_dir)

    return 0
