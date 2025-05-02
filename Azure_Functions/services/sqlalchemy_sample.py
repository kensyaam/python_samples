import logging
from sqlalchemy.dialects.postgresql import insert

from db.common import session_scope, model_to_dict
from db.models import Products, Customers, Orders

def select() -> list[dict]:
    """selectを実行する"""
    with session_scope() as session:
        # SQLAlchemy ORMを使用してデータを取得
        products = session.query(Products).all()

        # 結果を辞書のlistに変換
        products_list = [{"id": product.product_id, "name": product.product_name, "price": float(product.price)} for product in products]
        return products_list

def upsert(order_data: dict) -> None:
    """upsertを実行する (PostgreSQLのON CONFLICTを使用)"""
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

        orders = session.query(Orders).all()
        logging.info("AFTER:  order count: %s", len(orders))
        for row in orders:
            logging.info("  row: %s", model_to_dict(row))



def delete(product_id: int) -> None:
    """deleteを実行する"""
    with session_scope() as session:
        order = session.query(Orders).filter(Orders.product_id == product_id).first()
        session.delete(order)
        session.commit()

