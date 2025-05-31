import logging
import os
import sys
import traceback
from typing import Generator

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker

from db.models import Base, Customers, Orders, Products
from tests.func_runner import FuncRunner

logger = logging.getLogger("tests")


def stack_trace(stack_list):
    """
    traceback.extract_stack() の戻り値を引数に取り、
    スタックトレースを整形された文字列として返します。

    Args:
        stack_list: traceback.extract_stack() が返すトレースバックフレームのリスト。

    Returns:
        str: 整形されたスタックトレースの文字列。
    """
    formatted_stack = traceback.format_list(stack_list)
    # formatted_stack から .venv配下のパス、<frozen runpy>を除外
    formatted_stack = [
        line
        for line in formatted_stack
        if not ("<frozen runpy>" in line or ".venv" in line)
    ]
    # formatted_stack = [line for line in formatted_stack if "<frozen runpy>" not in line]
    # formatted_stack = [line for line in formatted_stack if ".venv" not in line]
    return "".join(formatted_stack)


def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    SQLAlchemyのbefore_cursor_executeイベントのハンドラー
    """
    # logger.debug("SQL: %s\n  Parameters: %s", statement, parameters)
    # logger.info("SQL: %s\n  Parameters: %s", statement, parameters)


def receive_commit(conn):
    """
    SQLAlchemyのcommitイベントのハンドラー
    """
    logger.info("Transaction committed.")
    # logger.info("Transaction committed. \n%s",
    #             stack_trace(traceback.extract_stack()))


def receive_rollback(conn):
    """
    SQLAlchemyのrollbackイベントのハンドラー
    """
    logger.info("Transaction rolled back.")
    # logger.info("Transaction rolled back. \n%s",
    #             stack_trace(traceback.extract_stack()))


# SQLAlchemyを用いたデータベース接続のセッティング
db_info = {
    "host": os.environ["DB_HOST"],
    "port": os.environ["DB_PORT"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "dbname": os.environ["DB_NAME"],
}


db_url = f"postgresql+psycopg://{db_info['user']}:{db_info['password']}@{db_info['host']}:{db_info['port']}/{db_info['dbname']}"
engine = create_engine(db_url)
event.listen(engine, "before_cursor_execute", before_cursor_execute)
event.listen(engine, "commit", receive_commit)
event.listen(engine, "rollback", receive_rollback)


# scoped_session
ScopedSession = scoped_session(
    sessionmaker(autocommit=False, autoflush=True, bind=engine)
)

Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    # logging.info("FIXTURE db_session Before")

    # テーブル作成
    Base.metadata.create_all(bind=engine)

    session = ScopedSession()
    try:
        yield session
    except Exception:
        session.rollback()  # errorが起こればrollback()
        raise
    finally:
        # logging.info("FIXTURE db_session After")
        session.close()  # どちらにせよ最終的にはclose()

    # テーブル削除
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def function_runner() -> Generator[FuncRunner, None, None] :
    print("Start fixture function_runner ...")
    runner = FuncRunner()
    runner.start()

    yield runner

    print("End fixture function_runner ...")
    runner.stop()


@pytest.fixture(scope="function")
def runner(function_runner) -> FuncRunner:
    print("Start fixture : runner ...")
    runner = function_runner
    runner.get_and_clear_log_lines()  # Clear logs before each test

    return runner
