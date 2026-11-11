import pytest
from sample_app import calculator as c


def test_add():
    assert c.add(2, 3) == 5


def test_subtract():
    assert c.subtract(10, 4) == 6


def test_divide_normal():
    assert c.divide(10, 4) == 2.5


def test_divide_by_zero_handled():
    # Expect a clean ValueError, not a crash
    with pytest.raises(ValueError):
        c.divide(5, 0)


def test_average_float():
    assert c.average([1, 2]) == 1.5


def test_average_empty():
    assert c.average([]) == 0


def test_percentage():
    assert c.percentage(1, 4) == 25.0
