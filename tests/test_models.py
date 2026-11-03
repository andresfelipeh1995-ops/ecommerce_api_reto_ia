from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app import models


def test_order_defaults(session_factory):
    with session_factory() as db:
        user = models.User(name="Ana", email="ana@correo.com", hashed_password="x")
        db.add(user)
        db.commit()
        order = models.Order(user_id=user.id, total_price=Decimal("10.00"))
        db.add(order)
        db.commit()
        assert order.status == models.OrderStatus.PENDING
        assert order.created_at is not None


def test_order_item_product_name(session_factory):
    with session_factory() as db:
        user = models.User(name="Ana", email="ana@correo.com", hashed_password="x")
        product = models.Product(name="Teclado", price=Decimal("10.00"), stock=5)
        db.add_all([user, product])
        db.commit()
        order = models.Order(user_id=user.id, total_price=Decimal("10.00"))
        order.items.append(
            models.OrderItem(product_id=product.id, quantity=1, unit_price=Decimal("10.00"))
        )
        db.add(order)
        db.commit()
        assert order.items[0].product_name == "Teclado"


def test_email_must_be_unique(session_factory):
    with session_factory() as db:
        db.add(models.User(name="A", email="dup@correo.com", hashed_password="x"))
        db.commit()
        db.add(models.User(name="B", email="dup@correo.com", hashed_password="x"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_negative_stock_is_rejected_by_database(session_factory):
    with session_factory() as db:
        db.add(models.Product(name="P", price=Decimal("10.00"), stock=-1))
        with pytest.raises(IntegrityError):
            db.commit()