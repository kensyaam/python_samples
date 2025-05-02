from invoke import task

@task
def hello(c):
    """hello world."""
    print("Hello, world!")

@task(help={"log_level": "CLIログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL). デフォルトは出力なし.",
            "expression": "テスト対象 (pytestの-kオプション). デフォルトは未指定."})
def test(c, log_level=None, expression=None):
    """Run tests."""
    log_cli_level = f"--log-cli-level={log_level}" if log_level else ''
    expression = f"-k {expression}" if expression else ''
    c.run(
        f"pytest -vv --disable-warnings --tb=short --color=yes "
        f"{log_cli_level} {expression}"
    )
    # c.run("pytest -vv --disable-warnings --tb=short --color=yes")
