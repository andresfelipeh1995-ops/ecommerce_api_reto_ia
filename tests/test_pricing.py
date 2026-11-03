from decimal import Decimal

import pytest

from app.config import settings
from app.services.pricing import final_unit_price


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        ("50.00", "50.00"),     # bajo el umbral: sin descuento
        ("100.00", "100.00"),   # justo en el umbral: sin descuento (regla es > 100)
        ("200.00", "180.00"),   # 10% de descuento
        ("150.55", "135.50"),   # redondeo ROUND_HALF_UP (135.495 -> 135.50)
    ],
)
def test_final_unit_price(price, expected):
    assert final_unit_price(Decimal(price)) == Decimal(expected)


def test_discount_percent_is_configurable(monkeypatch):
    monkeypatch.setattr(settings, "discount_percent", Decimal("20"))
    assert final_unit_price(Decimal("200.00")) == Decimal("160.00")