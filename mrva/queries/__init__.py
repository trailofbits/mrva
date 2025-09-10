import pathlib


CURDIR = pathlib.Path(__file__).parent
PRINT_AST_DIR = CURDIR / "print_ast"
PYTHON_PRINT_QUERY = PRINT_AST_DIR / "python" / "printAst.ql"
RUBY_PRINT_QUERY = PRINT_AST_DIR / "ruby" / "printAst.ql"

ALL_PRINT_QUERIES = {
    "python": PYTHON_PRINT_QUERY,
    "ruby": RUBY_PRINT_QUERY,
}
