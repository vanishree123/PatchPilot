import pytest

try:
    from buggy_discount import apply_discount
except ModuleNotFoundError:
    pytest.skip("This fixed test runs from its controlled demo workspace", allow_module_level=True)


def test_ten_percent_discount_is_applied_once():
    assert apply_discount(100) == 90
