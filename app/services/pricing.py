from decimal import ROUND_HALF_UP, Decimal

from app.config import settings

CENT = Decimal("0.01")


def final_unit_price(price: Decimal) -> Decimal:
    """Aplica el descuento porcentual configurable a productos sobre el umbral."""
    if price > settings.discount_threshold:
        discount = price * settings.discount_percent / Decimal("100")
        return (price - discount).quantize(CENT, rounding=ROUND_HALF_UP)
    return price