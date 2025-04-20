import azure.functions as func
import logging
import os
import json
from datetime import datetime

import psycopg

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy import Engine
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from models import Products, Customers, Orders

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

logging.getLogger().setLevel(logging.DEBUG)  # 全体のログレベルをDEBUGに設定

def get_current_datetime() -> datetime:
    """
    現在の日時を取得する

    Returns:
        datetime: 現在の日時
    """
    for_test = os.getenv("TEST_DATETIME")

    if for_test:
        # テスト用の環境変数が設定されている場合は、その値を使用
        try:
            return datetime.strptime(for_test, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            # raise ValueError("環境変数 TEST_DATETIME の値が日付フォーマットと一致しません。") from e
            logging.debug("環境変数 TEST_DATETIME の値が日付フォーマットと一致しません。 (%s)", str(e))

    # 環境変数が設定されていない場合は、現在の日時を取得
    return datetime.now()

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

@app.route(route="HttpExample")
def HttpExample(req: func.HttpRequest) -> func.HttpResponse:
    """
    HttpExample _summary_

    Args:
        req (func.HttpRequest): _description_

    Returns:
        func.HttpResponse: _description_
        aaaa
    """
    logging.error('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:

            
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )

@app.route(route="http_trigger2", auth_level=func.AuthLevel.ANONYMOUS)
def test2(req: func.HttpRequest) -> func.HttpResponse:
    """
    test2 _summary_

    Parameters
    ----------
    req : func.HttpRequest
        _description_

    Returns
    -------
    func.HttpResponse
        _description_
    """
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )



@app.route(route="db_access_sample", auth_level=func.AuthLevel.ANONYMOUS)
def db_access_whithout_sqlalchemy(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # PostgreSQL接続情報
        db_info = get_db_connection_info()

        # PostgreSQLに接続
        conn = psycopg.connect(
            host=db_info["host"],
            port=db_info["port"],
            user=db_info["user"],
            password=db_info["password"],
            dbname=db_info["dbname"]
        )

        # カーソルを作成
        cur = conn.cursor()

        # SQLクエリを実行
        cur.execute("SELECT * FROM products")

        # 結果を取得
        rows = cur.fetchall()

        # 結果をJSON形式に変換
        products = [{"id": row[0], "name": row[1], "price": float(row[2])} for row in rows]


        # 接続を閉じる
        cur.close()
        conn.close()

        return func.HttpResponse(
            body=json.dumps(products),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        return func.HttpResponse(
            body=f"Error: {str(e)}",
            status_code=500
        )


##########################################
# ここからSQLAlchemyを使用したDBアクセスのサンプル

def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    SQLAlchemyのbefore_cursor_executeイベントのハンドラー
    """
    logging.debug(f"SQL: {statement}")
    logging.debug(f"Parameters: {parameters}")

def create_sqlalchemy_engine() -> Engine:
    """
    SQLAlchemyエンジンを作成する

    Returns:
        Engine: SQLAlchemyエンジン
    """
    db_info = get_db_connection_info()
    db_url = f"postgresql://{db_info['user']}:{db_info['password']}@{db_info['host']}:{db_info['port']}/{db_info['dbname']}"
    # return create_engine(db_url, echo=True)
    engine = create_engine(db_url, echo=False)  # echo=Falseに設定

    # logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)  # SQLAlchemyのログレベルをDEBUGに設定

    event.listen(engine, "before_cursor_execute", before_cursor_execute)

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
        autocommit = False,
        autoflush = True,
        bind = engine)

    try:
        yield session  # with asでsessionを渡す

        # commitは必要な時に明示的に実行する
        # session.commit()  # 何も起こらなければcommit()
    except:
        session.rollback()  # errorが起こればrollback()
        raise
    finally:
        session.close()  # どちらにせよ最終的にはclose()

@app.route(route="db_access_sample2", auth_level=func.AuthLevel.ANONYMOUS)
def db_access_sample2(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # セッションを作成
        with session_scope() as session:
            # SQLAlchemy ORMを使用してデータを取得
            products = session.query(Products).all()

            # 結果をJSON形式に変換
            products_list = [{"id": product.product_id, "name": product.product_name, "price": float(product.price)} for product in products]

        return func.HttpResponse(
            body=json.dumps(products_list),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return func.HttpResponse(
            body=f"Error: {str(e)}",
            status_code=500
        )

@app.route(route="db_upsert_sample", auth_level=func.AuthLevel.ANONYMOUS)
def db_upsert_sample(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    product_id = req.params.get('product_id')

    order_data = {
        "order_id": 6,  # 主キーを指定
        "customer_id": 4,
        "product_id": product_id,
        "quantity": 3,
        "order_date": get_current_datetime()
    }

    try:
        # セッションを作成
        with session_scope() as session:
            stmt = insert(Orders).values(**order_data)
            stmt = stmt.on_conflict_do_update(
                constraint="orders_pkey",
                #set_=order_data
                set_={
                    "customer_id": stmt.excluded.customer_id,
                    "product_id": stmt.excluded.product_id,
                    "quantity": stmt.excluded.quantity,
                    "order_date": stmt.excluded.order_date
                }
            )
            session.execute(stmt)
            session.commit()

        return func.HttpResponse(
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return func.HttpResponse(
            body=f"Error: {str(e)}",
            status_code=500
        )

@app.route(route="db_delete_sample", auth_level=func.AuthLevel.ANONYMOUS)
def db_delete_sample(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    product_id = req.params.get('product_id')

    try:
        # セッションを作成
        with session_scope() as session:
            order = session.query(Orders).filter(Orders.product_id == product_id).first()
            session.delete(order)
            session.commit()

        return func.HttpResponse(
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return func.HttpResponse(
            body=f"Error: {str(e)}",
            status_code=500
        )