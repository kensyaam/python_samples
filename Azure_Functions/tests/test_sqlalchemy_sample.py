import logging
from datetime import datetime, date
import pytest
from unittest.mock import patch, MagicMock
from pytest_mock import MockerFixture
from factory import Factory, Faker
from factory.alchemy import SQLAlchemyModelFactory

from services import sqlalchemy_sample as target
from db.models import Products, Customers, Orders
from db.common import model_to_dict

from tests.conftest import logger
from tests.factories import ProductFactory, OrderFactory, CustomerFactory

# filepath: services/test_sqlalchemy_sample.py

def test_select(db_session):
    logging.info("test_select started")
    # Create db data
    products_data = [ProductFactory() for _ in range(3)]

    # Call the function
    result = target.select()

    # Verify the result
    expected = [
        {
            "id": product.product_id,
            "name": product.product_name,
            "price": float(product.price)
        }
        for product in products_data
    ]
    assert result == expected

def test_upsert_insert(db_session):
    logger.info("test_upsert started")
    # Create db data
    product = ProductFactory()
    customer = CustomerFactory()

    order_date = date(2023, 10, 1)

    order_data = {
        "customer_id": customer.customer_id,
        "product_id": product.product_id,
        "quantity": 5,
        "order_date": order_date.strftime("%Y-%m-%d"),
    }

    # Call the function
    target.upsert(order_data)

    # 別トランザクションでの変更を確認するために、セッションをリセット
    db_session.reset()

    # Verify the result
    order = (
        db_session.query(Orders)
        .filter(Orders.product_id == product.product_id)
        .first()
    )
    assert order is not None
    assert order.customer_id == order_data["customer_id"]
    assert order.product_id == order_data["product_id"]
    assert order.quantity == order_data["quantity"]
    assert order.order_date == order_date


def test_upsert_update(db_session):
    logger.info("test_upsert started")
    orders = db_session.query(Orders).all()
    logger.info("order count: %s", len(orders))

    # Create db data
    product = ProductFactory()
    customer = CustomerFactory()
    order = OrderFactory(customer=customer, product=product)

    orders = db_session.query(Orders).all()
    logger.info("BEFORE: order count: %s", len(orders))
    for row in orders:
        logger.info("  row: %s", model_to_dict(row))

    order_data = {
        "order_id": order.order_id,
        "quantity": order.quantity + 1,
        "order_date": order.order_date,
        "customer_id": order.customer_id,
        "product_id": order.product_id,
    }
    logger.info("param: %s", order_data)

    # Call the function
    target.upsert(order_data)

    # 別トランザクションでの変更を確認するために、セッションをリセット
    db_session.reset()

    # Verify the result
    order = (
        db_session.query(Orders)
        .filter(Orders.order_id == order.order_id)
        .first()
    )

    orders = db_session.query(Orders).all()
    logger.info("AFTER:  order count: %s", len(orders))
    for row in orders:
        logger.info("  row: %s", model_to_dict(row))

    assert order is not None
    assert order.customer_id == order_data["customer_id"]
    assert order.product_id == order_data["product_id"]
    assert order.quantity == order_data["quantity"]
    assert order.order_date == order_data["order_date"]
