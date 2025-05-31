from unittest.mock import MagicMock
from pytest_mock import MockerFixture

from services import sqlalchemy_sample as target
from db.models import Products

# filepath: c:\Users\Kensaku\dev\python_samples\Azure_Functions\services\test_sqlalchemy_sample.py

def test_select(mocker):
    # Mock session_scope and query results
    mock_session = MagicMock()
    mock_product = MagicMock(spec=Products)
    mock_product.product_id = 1
    mock_product.product_name = "Test Product"
    mock_product.price = 99.99

    mock = mocker.patch("services.sqlalchemy_sample.session_scope")
    mock.return_value.__enter__.return_value = mock_session
    mock_session.query.return_value.all.return_value = [mock_product]

    result = target.select()

    # Expected result
    expected = [{"id": 1, "name": "Test Product", "price": 99.99}]

    # Assertions
    assert result == expected
    mock_session.query.assert_called_once_with(Products)
    mock_session.query.return_value.all.assert_called_once()


