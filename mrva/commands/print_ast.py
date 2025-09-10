import logging
import subprocess
import sys
import tempfile

from mrva import queries
from mrva import types

logger = logging.getLogger(__name__)


async def main(args, argv):
    config = types.MRVAConfig.from_mrva_dir(args.mrva_dir)
    logger.info("Printing AST from mrva directory created at %s", config.created)

    kept, discarded = config.analyzable_repos(args.select, args.ignore)
    logger.info(
        "Found %d analyzable repositories, discarded %d", len(kept), len(discarded)
    )

    print_ast_template_path = queries.ALL_PRINT_QUERIES.get(args.language)
    if not print_ast_template_path:
        logger.error("Could not find print AST query for language %s", args.language)
        return 1

    for repo in kept:
        db_dir = repo.mrva_dir_db_dir(args.mrva_dir)
        query_pack_dir = print_ast_template_path.parent

        with (
            tempfile.NamedTemporaryFile(suffix=".bqrs") as output_fd,
            tempfile.NamedTemporaryFile(
                mode="w", dir=query_pack_dir, suffix=".ql"
            ) as query_fd,
        ):
            query_template_contents = print_ast_template_path.read_text()
            query_contents = query_template_contents.replace("{MRVA_MATCH}", args.match)
            query_fd.write(query_contents)
            query_fd.flush()

            logger.info("Printing AST for %s", repo.mrva_name)
            logger.debug("Print AST query contents %s", query_contents)

            command = [
                "codeql",
                "query",
                "run",
                "--database",
                db_dir,
                "--output",
                output_fd.name,
                query_fd.name,
            ]
            logger.debug("Full CodeQL command: %s", command)
            process = subprocess.run(
                command,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

            if process.returncode != 0:
                logger.warning(
                    "CodeQL query failed for %s returncode %d",
                    repo.mrva_name,
                    process.returncode,
                )
                continue

            command = [
                "codeql",
                "bqrs",
                "decode",
                "--entities",
                "url,string",
                output_fd.name,
            ]
            logger.debug("Full CodeQL command: %s", command)
            process = subprocess.run(
                command,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

            if process.returncode != 0:
                logger.warning(
                    "CodeQL BQRS decode failed for %s returncode %d",
                    repo.mrva_name,
                    process.returncode,
                )
                continue

    return 0
