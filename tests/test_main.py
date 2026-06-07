import argparse

import pytest

from mrva.main import parse_args


def test_run_top(tmp_path):
    args, _ = parse_args(
        [
            "run",
            "--token",
            "tok",
            "--controller-repo",
            "owner/ctrl",
            "--language",
            "python",
            str(tmp_path),
            "query.ql",
            "top",
            "--limit",
            "100",
        ]
    )
    assert args.command == "run"
    assert args.run_command == "top"
    assert args.limit == 100
    assert args.controller_repo == "owner/ctrl"
    assert args.language == "python"
    assert args.resume is None


def test_run_org(tmp_path):
    args, _ = parse_args(
        [
            "run",
            "--token",
            "tok",
            "--controller-repo",
            "owner/ctrl",
            "--language",
            "java",
            str(tmp_path),
            "query.ql",
            "org",
            "--owner",
            "myorg",
        ]
    )
    assert args.run_command == "org"
    assert args.owner == "myorg"


def test_run_repo(tmp_path):
    args, _ = parse_args(
        [
            "run",
            "--token",
            "tok",
            "--controller-repo",
            "owner/ctrl",
            "--language",
            "python",
            str(tmp_path),
            "query.ql",
            "repo",
            "--owner",
            "octocat",
            "--repository",
            "hello-world",
        ]
    )
    assert args.run_command == "repo"
    assert args.owner == "octocat"
    assert args.repository == "hello-world"


def test_run_query(tmp_path):
    args, _ = parse_args(
        [
            "run",
            "--token",
            "tok",
            "--controller-repo",
            "owner/ctrl",
            "--language",
            "python",
            str(tmp_path),
            "query.ql",
            "query",
            "--query",
            "language:python stars:>1000",
        ]
    )
    assert args.run_command == "query"
    assert args.query == "language:python stars:>1000"


def test_run_from_file(tmp_path):
    json_file = tmp_path / "repos.json"
    json_file.write_text('{"repositories": ["owner/repo"]}')
    args, _ = parse_args(
        [
            "run",
            "--token",
            "tok",
            "--controller-repo",
            "owner/ctrl",
            "--language",
            "python",
            str(tmp_path),
            "query.ql",
            "from-file",
            str(json_file),
        ]
    )
    assert args.run_command == "from-file"


def test_run_resume(tmp_path):
    args, _ = parse_args(
        [
            "run",
            "--token",
            "tok",
            "--resume",
            "42",
            str(tmp_path),
        ]
    )
    assert args.resume == 42
    assert args.run_command is None


def test_run_controller_repo_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MRVA_CONTROLLER_REPO", "env-owner/env-ctrl")
    args, _ = parse_args(
        [
            "run",
            "--token",
            "tok",
            "--language",
            "python",
            str(tmp_path),
            "query.ql",
            "top",
        ]
    )
    assert args.controller_repo == "env-owner/env-ctrl"


def test_run_language_required_without_resume(tmp_path):
    """--language must be provided for a fresh run (not resume)."""
    with pytest.raises(SystemExit):
        parse_args(
            [
                "run",
                "--token",
                "tok",
                "--controller-repo",
                "owner/ctrl",
                str(tmp_path),
                "query.ql",
                "top",
            ]
        )
    with pytest.raises((argparse.ArgumentTypeError, SystemExit)):
        parse_args(
            [
                "run",
                "--token",
                "tok",
                "--controller-repo",
                "owner/ctrl",
                "--language",
                "python",
                str(tmp_path / "nonexistent"),
                "query.ql",
                "top",
            ]
        )


def test_run_mrva_dir_must_exist(tmp_path):
    with pytest.raises((argparse.ArgumentTypeError, SystemExit)):
        parse_args(
            [
                "run",
                "--token",
                "tok",
                "--controller-repo",
                "owner/ctrl",
                "--language",
                "python",
                str(tmp_path / "nonexistent"),
                "query.ql",
                "top",
            ]
        )
