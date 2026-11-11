"""Simple calculator module (contains intentional bugs for the demo)."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def divide(a, b):
    # BUG: no guard against division by zero
    return a / b


def average(values):
    # BUG: crashes on empty list, and uses integer division
    return sum(values) // len(values)


def percentage(part, whole):
    if whole == 0:
        return 0.0
    return round(part / whole * 100, 2)
