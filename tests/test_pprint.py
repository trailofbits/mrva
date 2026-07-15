from mrva import commands
from mrva import main
from mrva import types

CONTEXT = types.Context(before=0, after=0)


async def test_pprint_problem_query_no_contents(capsys, problem_query_mrva_dir):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "no-contents",
            "--context",
            "0",
            str(problem_query_mrva_dir),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "https://github.com/someorg/no-contents/blob/ffffffff/code.py#L1-L1",
        "https://github.com/someorg/no-contents/blob/ffffffff/code.py#L5-L5",
        "https://github.com/someorg/no-contents/blob/ffffffff/code.py#L9-L9",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_problem_query_with_contents(capsys, problem_query_mrva_dir):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "with-contents",
            "--context",
            "0",
            str(problem_query_mrva_dir),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "1 class A:",
        "5 class B:",
        "9 class C:",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_problem_query_no_contents_sarif(
    capsys, problem_query_no_contents_sarif
):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "no-contents",
            "--context",
            "0",
            str(problem_query_no_contents_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "(ln: 1:1 col: 1:9)",
        "(ln: 5:5 col: 1:9)",
        "(ln: 9:9 col: 1:9)",
    ]
    not_expected = [
        "1 class A:",
        "5 class B:",
        "9 class C:",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out
    for e in not_expected:
        assert e not in result.out


async def test_pprint_problem_query_with_contents_sarif(
    capsys, problem_query_with_contents_sarif
):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "with-contents",
            "--context",
            "0",
            str(problem_query_with_contents_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "(ln: 1:1 col: 1:9)",
        "(ln: 5:5 col: 1:9)",
        "(ln: 9:9 col: 1:9)",
        "1 class A:",
        "5 class B:",
        "9 class C:",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_problem_query_with_snippets_sarif(
    capsys, problem_query_with_snippets_sarif
):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "with-contents",
            "--context",
            "0",
            str(problem_query_with_snippets_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "(ln: 1:1 col: 1:9)",
        "(ln: 5:5 col: 1:9)",
        "(ln: 9:9 col: 1:9)",
        "1 class A:",
        "5 class B:",
        "9 class C:",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_path_problem_query_with_snippets_sarif(
    capsys, path_problem_query_with_snippets_sarif
):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "with-contents",
            "--context",
            "0",
            str(path_problem_query_with_snippets_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        '4 directory = os.getenv("SOME_DIRECTORY")',
        '6 path1 = f"{directory}/SOME_FILE1.txt"',
        "7 fd1 = os.open(path1)",
        '11 path2 = f"{directory}/SOME_FILE2.txt"',
        "12 fd2 = os.open(path2)",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_problem_query_with_contents_repo_url(
    capsys, problem_query_with_contents_sarif
):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "with-contents",
            "--context",
            "0",
            "--repo-url",
            "https://github.com/someorg/somerepo/blog/abcdef",
            str(problem_query_with_contents_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "https://github.com/someorg/somerepo/blog/abcdef/code.py#L1-L1",
        "https://github.com/someorg/somerepo/blog/abcdef/code.py#L5-L5",
        "https://github.com/someorg/somerepo/blog/abcdef/code.py#L9-L9",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_path_problem_query_no_contents(
    capsys, path_problem_query_mrva_dir
):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "no-contents",
            "--context",
            "0",
            str(path_problem_query_mrva_dir),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "https://github.com/someorg/no-contents/blob/ffffffff/code.py#L4-L4",
        "https://github.com/someorg/no-contents/blob/ffffffff/code.py#L6-L6",
        "https://github.com/someorg/no-contents/blob/ffffffff/code.py#L7-L7",
        "https://github.com/someorg/no-contents/blob/ffffffff/code.py#L11-L11",
        "https://github.com/someorg/no-contents/blob/ffffffff/code.py#L12-L12",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_path_problem_query_with_contents_flows(
    capsys,
    path_problem_query_mrva_dir,
):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "with-contents",
            "--context",
            "0",
            str(path_problem_query_mrva_dir),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        '4 directory = os.getenv("SOME_DIRECTORY")',
        '6 path1 = f"{directory}/SOME_FILE1.txt"',
        "7 fd1 = os.open(path1)",
        '11 path2 = f"{directory}/SOME_FILE2.txt"',
        "12 fd2 = os.open(path2)",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_semgrep_sarif(capsys, semgrep_sarif):
    args = main.parse_args(
        [
            "pprint",
            "--context",
            "0",
            str(semgrep_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "(ln: 3:3 col: 1:19)",
        "(ln: 5:5 col: 1:34)",
        "(ln: 7:10 col: 1:2)",
        '3 API_KEY = "abc123"',
        '5 subprocess.call("ls", shell=True)',
        "7 subprocess.call(",
        '8     "grep foo",',
        "9     shell=True,",
        "10 )",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_semgrep_sarif_select_id(capsys, semgrep_sarif):
    args = main.parse_args(
        [
            "pprint",
            "--context",
            "0",
            "--select-id",
            "hardcoded*",
            str(semgrep_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()

    assert code == 0
    assert "hardcoded-api-key" in result.out
    assert "shell-injection-risk" not in result.out


async def test_pprint_semgrep_sarif_ignore_id(capsys, semgrep_sarif):
    args = main.parse_args(
        [
            "pprint",
            "--context",
            "0",
            "--ignore-id",
            "hardcoded*",
            str(semgrep_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()

    assert code == 0
    assert "hardcoded-api-key" not in result.out
    assert "shell-injection-risk" in result.out


async def test_pprint_semgrep_sarif_select_path(capsys, semgrep_sarif):
    args = main.parse_args(
        [
            "pprint",
            "--context",
            "0",
            "--select-path",
            "vendor/*",
            str(semgrep_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()

    assert code == 0
    assert "vendor/lib.py" in result.out
    assert '"grep foo"' not in result.out


async def test_pprint_semgrep_sarif_ignore_path(capsys, semgrep_sarif):
    args = main.parse_args(
        [
            "pprint",
            "--context",
            "0",
            "--ignore-path",
            "vendor/*",
            str(semgrep_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()

    assert code == 0
    assert "vendor/lib.py" not in result.out
    assert '"grep foo"' in result.out


async def test_pprint_semgrep_sarif_select_id_and_ignore_path(capsys, semgrep_sarif):
    args = main.parse_args(
        [
            "pprint",
            "--context",
            "0",
            "--select-id",
            "hardcoded*",
            "--ignore-path",
            "vendor/*",
            str(semgrep_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()

    assert code == 0
    assert '3 API_KEY = "abc123"' in result.out
    assert "vendor/lib.py" not in result.out
    assert "shell-injection-risk" not in result.out


async def test_pprint_problem_query_select_id_no_matches(
    capsys, problem_query_with_snippets_sarif
):
    args = main.parse_args(
        [
            "pprint",
            "--context",
            "0",
            "--select-id",
            "nonexistent-rule",
            str(problem_query_with_snippets_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()

    assert code == 0
    assert "class A:" not in result.out
    assert "class B:" not in result.out


async def test_pprint_semgrep_sarif_repo_url(capsys, semgrep_sarif):
    args = main.parse_args(
        [
            "pprint",
            "--context",
            "0",
            "--repo-url",
            "https://github.com/someorg/somerepo/blob/abcdef",
            str(semgrep_sarif),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "https://github.com/someorg/somerepo/blob/abcdef/code.py#L3-L3",
        "https://github.com/someorg/somerepo/blob/abcdef/code.py#L5-L5",
        "https://github.com/someorg/somerepo/blob/abcdef/code.py#L7-L10",
    ]

    assert code == 0
    for e in expected:
        assert e in result.out


async def test_pprint_path_problem_query_with_contents_no_flows(
    capsys,
    path_problem_query_mrva_dir,
):
    args = main.parse_args(
        [
            "pprint",
            "--select",
            "with-contents",
            "--context",
            "0",
            "--no-flows",
            str(path_problem_query_mrva_dir),
        ]
    )
    code = await commands.pprint.main(*args)
    result = capsys.readouterr()
    expected = [
        "7 fd1 = os.open(path1)",
        "12 fd2 = os.open(path2)",
    ]
    not_expected = [
        '4 directory = os.getenv("SOME_DIRECTORY")',
        '6 path1 = f"{directory}/SOME_FILE1.txt"',
        '11 path2 = f"{directory}/SOME_FILE2.txt"',
    ]

    assert code == 0
    for e in expected:
        assert e in result.out
    for ne in not_expected:
        assert ne not in result.out
