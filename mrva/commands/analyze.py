import logging
import subprocess
import sys

from mrva import types

logger = logging.getLogger(__name__)


async def main(args, argv):
    config = types.MRVAConfig.from_mrva_dir(args.mrva_dir)
    logger.info("Analyzing mrva directory created at %s", config.created)

    kept, discarded = config.analyzable_repos(args.select, args.ignore)
    logger.info(
        "Found %d analyzable repositories, discarded %d", len(kept), len(discarded)
    )

    total_results = 0
    for repo in kept:
        output_path = repo.mrva_dir_sarif_path(args.mrva_dir)
        db_dir = repo.mrva_dir_db_dir(args.mrva_dir)
        command = [
            "codeql",
            "database",
            "analyze",
            "--format",
            "sarif-latest",
            "--sarif-add-file-contents",
            "--output",
            output_path,
            *argv,
            "--",
            db_dir,
            args.queries,
        ]

        try:
            logger.info("Running CodeQL analysis on %s", repo.mrva_name)
            logger.debug("Full CodeQL command: %s", command)
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
                repo.mrva_name,
                process.returncode,
            )
            continue

        output = types.SARIFOutput.from_path(output_path)
        repo_result_count = len(output.results)
        total_results += repo_result_count
        logger.info("Found %d results for %s", repo_result_count, repo.mrva_name)

    logger.info("Found %d total results for %s", total_results, args.mrva_dir)

    return 0
