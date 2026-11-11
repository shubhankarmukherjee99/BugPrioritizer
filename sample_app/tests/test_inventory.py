import pytest
from sample_app.inventory import Inventory, apply_discount, checkout, fetch_exchange_rate


@pytest.fixture
def inv():
    i = Inventory()
    i.add_item("pen", 10, 5.0)
    i.add_item("book", 2, 250.0)
    return i


def test_total_value(inv):
    assert inv.total_value() == 550.0


def test_remove_unknown_item(inv):
    with pytest.raises(ValueError):
        inv.remove_item("laptop", 1)


def test_stock_never_negative(inv):
    with pytest.raises(ValueError):
        inv.remove_item("pen", 50)


def test_discount_reduces_price():
    assert apply_discount(1000, 10) == 900.0


def test_checkout(inv):
    assert checkout({"pen": 2, "book": 1}, inv) == 260.0


def test_exchange_rate_service():
    assert fetch_exchange_rate() > 0
