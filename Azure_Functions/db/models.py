from typing import List, Optional

from sqlalchemy import Date, ForeignKeyConstraint, Integer, Numeric, PrimaryKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
import decimal


class Base(DeclarativeBase):
    pass


class Customers(Base):
    __tablename__ = 'customers'
    __table_args__ = (
        PrimaryKeyConstraint('customer_id', name='customers_pkey'),
        UniqueConstraint('email', name='customers_email_key')
    )

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))

    orders: Mapped[List['Orders']] = relationship(
        'Orders', back_populates='customer')


class Products(Base):
    __tablename__ = 'products'
    __table_args__ = (
        PrimaryKeyConstraint('product_id', name='products_pkey'),
    )

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(String(255))
    price: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2))

    orders: Mapped[List['Orders']] = relationship(
        'Orders', back_populates='product')


class Orders(Base):
    __tablename__ = 'orders'
    __table_args__ = (
        ForeignKeyConstraint(
            ['customer_id'], ['customers.customer_id'], name='orders_customer_id_fkey'),
        ForeignKeyConstraint(
            ['product_id'], ['products.product_id'], name='orders_product_id_fkey'),
        PrimaryKeyConstraint('order_id', name='orders_pkey')
    )

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    order_date: Mapped[datetime.date] = mapped_column(Date)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer)
    product_id: Mapped[Optional[int]] = mapped_column(Integer)

    customer: Mapped[Optional['Customers']] = relationship(
        'Customers', back_populates='orders')
    product: Mapped[Optional['Products']] = relationship(
        'Products', back_populates='orders')
