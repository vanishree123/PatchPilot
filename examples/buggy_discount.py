"""Built-in PatchPilot example: the discount is mistakenly subtracted twice."""


def apply_discount(price):
    discount = price * 0.10
    return price - discount - discount
