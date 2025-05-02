# Register this blueprint by adding the following line of code
# to your entry point file.
# app.register_functions(blueprint)
#
# Please refer to https://aka.ms/azure-functions-python-blueprints


import logging
import azure.functions as func

import os
import json
from datetime import datetime

from services import psycopg_sample
from services import sqlalchemy_sample


blueprint = func.Blueprint()


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


@blueprint.route(route="http_trigger", auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
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


@blueprint.route(route="db_access_sample", auth_level=func.AuthLevel.ANONYMOUS)
def db_access_whithout_sqlalchemy(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        products = psycopg_sample.select()

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


@blueprint.route(route="db_select_sample", auth_level=func.AuthLevel.ANONYMOUS)
def db_select_sample(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        products = sqlalchemy_sample.select()

        return func.HttpResponse(
            body=json.dumps(products),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return func.HttpResponse(
            body=f"Error: {str(e)}",
            status_code=500
        )

@blueprint.route(route="db_upsert_sample", auth_level=func.AuthLevel.ANONYMOUS)
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
        sqlalchemy_sample.upsert(order_data)

        return func.HttpResponse(
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return func.HttpResponse(
            body=f"Error: {str(e)}",
            status_code=500
        )

@blueprint.route(route="db_delete_sample", auth_level=func.AuthLevel.ANONYMOUS)
def db_delete_sample(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    product_id = req.params.get('product_id')

    try:
        sqlalchemy_sample.delete(int(product_id))

        return func.HttpResponse(
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return func.HttpResponse(
            body=f"Error: {str(e)}",
            status_code=500
        )
