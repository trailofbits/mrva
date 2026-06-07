import base64
import pathlib
import subprocess
import unittest.mock

import pytest

from mrva import pack


def _make_fake_bundle(tmp_path):
    """Simulate codeql writing a bundle by creating a fake tgz."""

    def fake_run(cmd, **kwargs):
        # Find the -o argument and write a fake file there
        o_idx = cmd.index("-o")
        out_path = pathlib.Path(cmd[o_idx + 1])
        out_path.write_bytes(b"fake-tgz-content")
        result = unittest.mock.MagicMock()
        result.returncode = 0
        return result

    return fake_run


def test_build_query_pack_bare_ql(tmp_path):
    """A bare .ql file with no qlpack should synthesize a pack, install, then bundle."""
    query_file = tmp_path / "MyQuery.ql"
    query_file.write_text("select 1")

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "bundle" in cmd:
            o_idx = cmd.index("-o")
            pathlib.Path(cmd[o_idx + 1]).write_bytes(b"fake-tgz")
        result = unittest.mock.MagicMock()
        result.returncode = 0
        return result

    with unittest.mock.patch("mrva.pack._run", side_effect=fake_run):
        result = pack.build_query_pack(query_file, "python", tmp_path)

    assert len(calls) == 2
    # First call: pack install
    assert calls[0][:3] == ["codeql", "pack", "install"]
    # Second call: pack bundle --mrva
    assert calls[1][:4] == ["codeql", "pack", "bundle", "--mrva"]
    assert "--query" in calls[1]
    assert "-o" in calls[1]

    # Result is valid base64
    assert base64.b64decode(result) == b"fake-tgz"

    # Synthesized qlpack.yml should reference the language
    pack_dir = tmp_path / "query-pack"
    qlpack_text = (pack_dir / "qlpack.yml").read_text()
    assert "codeql/python-all" in qlpack_text
    assert "MyQuery.ql" in qlpack_text


def test_build_query_pack_ql_with_existing_pack(tmp_path):
    """A .ql file that sits inside an existing pack should skip synthesis and install."""
    pack_dir = tmp_path / "mypack"
    pack_dir.mkdir()
    (pack_dir / "qlpack.yml").write_text("name: mypack\nversion: 0.0.0\n")
    query_file = pack_dir / "MyQuery.ql"
    query_file.write_text("select 1")

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "bundle" in cmd:
            o_idx = cmd.index("-o")
            pathlib.Path(cmd[o_idx + 1]).write_bytes(b"fake-tgz")
        result = unittest.mock.MagicMock()
        result.returncode = 0
        return result

    with unittest.mock.patch("mrva.pack._run", side_effect=fake_run):
        result = pack.build_query_pack(query_file, "python", tmp_path)

    # Only one call: bundle (no install)
    assert len(calls) == 1
    assert calls[0][:4] == ["codeql", "pack", "bundle", "--mrva"]
    assert "--query" in calls[0]
    assert base64.b64decode(result) == b"fake-tgz"


def test_build_query_pack_directory(tmp_path):
    """A pack directory should be bundled directly with no --query flag."""
    pack_dir = tmp_path / "mypack"
    pack_dir.mkdir()
    (pack_dir / "qlpack.yml").write_text("name: mypack\nversion: 0.0.0\n")

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "bundle" in cmd:
            o_idx = cmd.index("-o")
            pathlib.Path(cmd[o_idx + 1]).write_bytes(b"fake-tgz")
        result = unittest.mock.MagicMock()
        result.returncode = 0
        return result

    with unittest.mock.patch("mrva.pack._run", side_effect=fake_run):
        result = pack.build_query_pack(pack_dir, "python", tmp_path)

    assert len(calls) == 1
    assert calls[0][:4] == ["codeql", "pack", "bundle", "--mrva"]
    assert "--query" not in calls[0]
    assert base64.b64decode(result) == b"fake-tgz"


def test_build_query_pack_codeql_failure(tmp_path):
    """If codeql fails, the CalledProcessError should propagate."""
    query_file = tmp_path / "MyQuery.ql"
    query_file.write_text("select 1")

    with unittest.mock.patch(
        "mrva.pack._run",
        side_effect=subprocess.CalledProcessError(1, "codeql"),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            pack.build_query_pack(query_file, "python", tmp_path)
