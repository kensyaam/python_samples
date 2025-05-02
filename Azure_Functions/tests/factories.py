import factory
from factory import fuzzy
import decimal
from sqlalchemy.orm import Session
from db.models import Customers, Products, Orders  # モデルのインポートパスに合わせて修正してください

from tests.conftest import ScopedSession

class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        sqlalchemy_session = ScopedSession
        sqlalchemy_session_persistence = 'commit'
        abstract = True

class CustomerFactory(BaseFactory):
    class Meta:
        model = Customers

    customer_id = factory.Sequence(lambda n: n)
    customer_name = factory.Faker('name')
    email = factory.Faker('email')

    @factory.post_generation
    def orders(obj, create, extract, **kwargs):
        if not create:
            return

        if extract:
            for order in extract:
                obj.orders.append(order)


class ProductFactory(BaseFactory):
    class Meta:
        model = Products

    product_id = factory.Sequence(lambda n: n)
    product_name = factory.Faker('word')
    price = fuzzy.FuzzyDecimal(low=1.0, high=1000.0, precision=2)

    @factory.post_generation
    def orders(obj, create, extract, **kwargs):
        if not create:
            return

        if extract:
            for order in extract:
                obj.orders.append(order)

class OrderFactory(BaseFactory):
    class Meta:
        model = Orders

    order_id = factory.Sequence(lambda n: n)
    quantity = factory.fuzzy.FuzzyInteger(low=1, high=10)
    order_date = factory.Faker('date_this_decade')
    customer = factory.SubFactory(CustomerFactory)
    product = factory.SubFactory(ProductFactory)
    customer_id = factory.SelfAttribute('customer.customer_id')
    product_id = factory.SelfAttribute('product.product_id')

if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db.models import Base

    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    BaseFactory.Meta.sqlalchemy_session = session

    # Customerの作成
    customer1 = CustomerFactory.create()
    customer2 = CustomerFactory.create(email=None)
    print(f"Created Customer: {customer1.customer_id}, {customer1.customer_name}, {customer1.email}")
    print(f"Created Customer: {customer2.customer_id}, {customer2.customer_name}, {customer2.email}")

    # Productの作成
    product1 = ProductFactory.create()
    product2 = ProductFactory.create(price=decimal.Decimal('50.00'))
    print(f"Created Product: {product1.product_id}, {product1.product_name}, {product1.price}")
    print(f"Created Product: {product2.product_id}, {product2.product_name}, {product2.price}")

    # Orderの作成（CustomerとProductを自動的に関連付け）
    order1 = OrderFactory.create()
    print(f"Created Order: {order1.order_id}, Quantity: {order1.quantity}, Date: {order1.order_date}, Customer ID: {order1.customer_id}, Product ID: {order1.product_id}")
    print(f"  Customer: {order1.customer.customer_name}, Product: {order1.product.product_name}")

    # 特定のCustomerに複数のOrderを関連付ける
    customer_with_orders = CustomerFactory.create(orders=factory.List([
        OrderFactory.build(product=ProductFactory.create()),
        OrderFactory.build(product=ProductFactory.create()),
    ]))
    print(f"\nCreated Customer with Orders: {customer_with_orders.customer_name}")
    for order in customer_with_orders.orders:
        print(f"  Order ID: {order.order_id}, Product: {order.product.product_name}")

    session.close()
