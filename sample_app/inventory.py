"""Inventory / payment module (contains intentional bugs for the demo)."""
import random


class Inventory:
    def __init__(self):
        self.items = {}

    def add_item(self, name, qty, price):
        if qty < 0 or price < 0:
            raise ValueError("qty and price must be non-negative")
        if name in self.items:
            self.items[name]["qty"] += qty
        else:
            self.items[name] = {"qty": qty, "price": price}

    def remove_item(self, name, qty):
        # BUG: KeyError on unknown item, and allows stock to go negative
        self.items[name]["qty"] -= qty

    def total_value(self):
        return sum(i["qty"] * i["price"] for i in self.items.values())


def apply_discount(amount, percent):
    # BUG: discount is added instead of subtracted -> customers overcharged
    return round(amount + amount * percent / 100, 2)


def checkout(cart, inventory):
    total = 0
    for name, qty in cart.items():
        price = inventory.items[name]["price"]
        total += price * qty
    return round(total, 2)


def fetch_exchange_rate():
    # Simulates an unreliable network call -> produces a FLAKY test
    if random.random() < 0.5:
        raise TimeoutError("exchange-rate service timed out")
    return 83.2
