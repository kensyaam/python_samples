import os
import logging

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy import Engine
from sqlalchemy import event
from sqlalchemy.orm import Session

def get_db_connection_info() -> dict:
    """
    環境変数からDB接続情報を取得する

    Returns:
        dict: DB接続情報
    """
    return {
        "host": os.environ["DB_HOST"],
        "port": os.environ["DB_PORT"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "dbname": os.environ["DB_NAME"]
    }

def get_db_url() -> str:
    """
    DB接続URLを取得する

    Returns:
        str: DB接続URL
    """
    db_info = get_db_connection_info()
    db_url = f"postgresql+psycopg://{db_info['user']}:{db_info['password']}@{db_info['host']}:{db_info['port']}/{db_info['dbname']}"
    return db_url

def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    SQLAlchemyのbefore_cursor_executeイベントのハンドラー
    """
    # logging.debug("SQL: %s\n  Parameters: %s", statement, parameters)
    logging.info("SQL: %s\n  Parameters: %s", statement, parameters)

def receive_commit(conn):
    """
    SQLAlchemyのcommitイベントのハンドラー
    """
    logging.info("Transaction committed.")

def receive_rollback(conn):
    """
    SQLAlchemyのrollbackイベントのハンドラー
    """
    logging.info("Transaction rolled back.")

def create_sqlalchemy_engine() -> Engine:
    """
    SQLAlchemyエンジンを作成する

    Returns:
        Engine: SQLAlchemyエンジン
    """
    db_url = get_db_url()
    # return create_engine(db_url, echo=True)
    engine = create_engine(db_url, echo=False)  # echo=Falseに設定

    # logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)  # SQLAlchemyのログレベルをDEBUGに設定

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "commit", receive_commit)
    event.listen(engine, "rollback", receive_rollback)

    return engine

@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Sessionのcontextmnager.

    Yields:
        Generator[Session, None, None]: _description_
    """
    # SQLAlchemyエンジンを作成
    engine = create_sqlalchemy_engine()

    session = Session(
        autocommit=False,
        autoflush=True,
        bind=engine)

    try:
        yield session  # with asでsessionを渡す

        # commitは必要な時に明示的に実行する
        # session.commit()  # 何も起こらなければcommit()
    except Exception:
        session.rollback()  # errorが起こればrollback()
        raise
    finally:
        session.close()  # どちらにせよ最終的にはclose()


def model_to_dict(model_instance):
    data = {}
    for column in model_instance.__table__.columns:
        data[column.name] = getattr(model_instance, column.name)
    return data
