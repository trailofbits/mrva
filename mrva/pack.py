import base64
import pathlib
import shutil
import subprocess

QLPACK_FILENAMES = ("qlpack.yml", "codeql-pack.yml")
QUERY_PACK_NAME = "codeql-remote/query"


def _find_qlpack(path):
    """Walk up from path looking for a qlpack.yml or codeql-pack.yml."""
    current = pathlib.Path(path).parent
    while True:
        for name in QLPACK_FILENAMES:
            if (current / name).exists():
                return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _synthesize_pack(query_path, language, pack_dir):
    """Copy query into pack_dir and write a synthetic qlpack.yml."""
    query_path = pathlib.Path(query_path)
    dest = pack_dir / query_path.name
    shutil.copy2(query_path, dest)

    qlpack = (
        f"name: {QUERY_PACK_NAME}\n"
        f"version: 0.0.0\n"
        f"dependencies:\n"
        f'  "codeql/{language}-all": "*"\n'
        f"defaultSuite:\n"
        f"  - description: Query suite for variant analysis\n"
        f"  - query: {query_path.name}\n"
    )
    (pack_dir / "qlpack.yml").write_text(qlpack)
    return dest


def _run(cmd):
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result


def build_query_pack(query_path, language, tmp_dir):
    """
    Build a base64-encoded MRVA query pack tgz from a .ql file or pack directory.

    Args:
        query_path: Path to a .ql file or a qlpack root directory.
        language:   CodeQL language string (e.g. "python").
        tmp_dir:    Writable temp directory for intermediate files.

    Returns:
        Base64-encoded string of the bundle tgz.
    """
    query_path = pathlib.Path(query_path)
    tmp_dir = pathlib.Path(tmp_dir)
    bundle_path = tmp_dir / "bundle.tgz"

    if query_path.is_dir():
        # Existing pack directory — bundle directly.
        pack_dir = query_path
        query_args = []
        _run(
            [
                "codeql",
                "pack",
                "bundle",
                "--mrva",
                "-o",
                str(bundle_path),
                str(pack_dir),
                *query_args,
            ]
        )
    else:
        # Bare .ql file — synthesize or use existing pack.
        existing_pack = _find_qlpack(query_path)
        if existing_pack:
            pack_dir = existing_pack
            query_args = ["--query", str(query_path)]
        else:
            pack_dir = tmp_dir / "query-pack"
            pack_dir.mkdir(exist_ok=True)
            query_file = _synthesize_pack(query_path, language, pack_dir)
            _run(["codeql", "pack", "install", str(pack_dir)])
            query_args = ["--query", str(query_file)]

        _run(
            [
                "codeql",
                "pack",
                "bundle",
                "--mrva",
                *query_args,
                "-o",
                str(bundle_path),
                str(pack_dir),
            ]
        )

    return base64.b64encode(bundle_path.read_bytes()).decode()
