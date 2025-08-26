from mrva import commands
from mrva import main

CONTEXT = commands.pprint.Context(before=0, after=0)


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
