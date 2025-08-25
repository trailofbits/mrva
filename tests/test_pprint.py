from mrva import commands
from mrva import types

REPO = types.MRVARepo(
    url="https://github.com/someorg/somerepo",
    download_success=True,
    mrva_name="mrva-python-someorg-somerepo",
    db_dir="db",
    commit="ffffffffffffffffffffffffffffffffffffffff",
)
CONTEXT = commands.pprint.Context(before=0, after=0)


def test_pprint_problem_query_no_contents(capsys, problem_query_no_contents):
    commands.pprint.print_sarif_output(REPO, problem_query_no_contents, CONTEXT)
    result = capsys.readouterr()
    expected = [
        "https://github.com/someorg/somerepo/blob/ffffffff/code.py#L1-L1",
        "https://github.com/someorg/somerepo/blob/ffffffff/code.py#L5-L5",
        "https://github.com/someorg/somerepo/blob/ffffffff/code.py#L9-L9",
    ]

    for e in expected:
        assert e in result.out


def test_pprint_problem_query_with_contents(capsys, problem_query_with_contents):
    commands.pprint.print_sarif_output(REPO, problem_query_with_contents, CONTEXT)
    result = capsys.readouterr()
    expected = [
        "1 class A:",
        "5 class B:",
        "9 class C:",
    ]

    for e in expected:
        assert e in result.out


def test_pprint_path_problem_query_no_contents(capsys, path_problem_query_no_contents):
    commands.pprint.print_sarif_output(REPO, path_problem_query_no_contents, CONTEXT)
    result = capsys.readouterr()
    expected = [
        "https://github.com/someorg/somerepo/blob/ffffffff/code.py#L4-L4",
        "https://github.com/someorg/somerepo/blob/ffffffff/code.py#L6-L6",
        "https://github.com/someorg/somerepo/blob/ffffffff/code.py#L7-L7",
        "https://github.com/someorg/somerepo/blob/ffffffff/code.py#L11-L11",
        "https://github.com/someorg/somerepo/blob/ffffffff/code.py#L12-L12",
    ]

    for e in expected:
        assert e in result.out


def test_pprint_path_problem_query_with_contents_no_flows(
    capsys,
    path_problem_query_with_contents,
):
    commands.pprint.print_sarif_output(
        REPO, path_problem_query_with_contents, CONTEXT, flows=False
    )
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

    for e in expected:
        assert e in result.out

    for ne in not_expected:
        assert ne not in result.out
