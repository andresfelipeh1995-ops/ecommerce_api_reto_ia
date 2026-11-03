from decimal import Decimal

import pytest

from app import models, schemas
from app.services import order_service


def test_order_requires_authentication(client):
    resp = client.post("/orders/", json={"items": [{"product_id": 1, "quantity": 1}]})
    assert resp.status_code == 401


def test_order_applies_discount_and_reduces_stock(
    client, make_user, make_product, get_stock, place_order
):
    user = make_user()
    pid = make_product(name="Monitor", price="200.00", stock=5)

    order = place_order(user["headers"], [{"product_id": pid, "quantity": 2}])

    assert Decimal(order["total_price"]) == Decimal("360.00")  # (200 - 10%) x 2
    assert order["status"] == "pending"
    assert order["items"][0]["product_name"] == "Monitor"
    assert Decimal(order["items"][0]["unit_price"]) == Decimal("180.00")
    assert get_stock(pid) == 3


def test_order_without_discount_below_threshold(client, make_user, make_product, place_order):
    user = make_user()
    pid = make_product(price="50.00")
    order = place_order(user["headers"], [{"product_id": pid, "quantity": 3}])
    assert Decimal(order["total_price"]) == Decimal("150.00")


def test_order_with_multiple_products(client, make_user, make_product, place_order):
    user = make_user()
    cheap = make_product(name="Barato", price="10.00")
    expensive = make_product(name="Caro", price="200.00")
    order = place_order(
        user["headers"],
        [{"product_id": cheap, "quantity": 2}, {"product_id": expensive, "quantity": 1}],
    )
    assert Decimal(order["total_price"]) == Decimal("200.00")  # 20 + 180
    assert len(order["items"]) == 2


def test_order_rejects_insufficient_stock(client, make_user, make_product, get_stock):
    user = make_user()
    pid = make_product(stock=1)
    resp = client.post(
        "/orders/",
        json={"items": [{"product_id": pid, "quantity": 2}]},
        headers=user["headers"],
    )
    assert resp.status_code == 409
    assert "disponible: 1" in resp.json()["detail"]
    assert get_stock(pid) == 1


def test_order_rejects_nonexistent_product(client, make_user):
    user = make_user()
    resp = client.post(
        "/orders/",
        json={"items": [{"product_id": 999, "quantity": 1}]},
        headers=user["headers"],
    )
    assert resp.status_code == 400


def test_order_rejects_empty_and_duplicate_items(client, make_user):
    user = make_user()
    assert client.post("/orders/", json={"items": []}, headers=user["headers"]).status_code == 422
    dup = {"items": [{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 1}]}
    assert client.post("/orders/", json=dup, headers=user["headers"]).status_code == 422


def test_failed_order_is_atomic(client, make_user, make_product, get_stock, session_factory):
    """Si un producto falla, no debe descontarse el stock de los anteriores."""
    user = make_user()
    ok = make_product(name="Ok", stock=5)
    short = make_product(name="Corto", stock=1)

    resp = client.post(
        "/orders/",
        json={
            "items": [
                {"product_id": ok, "quantity": 2},
                {"product_id": short, "quantity": 9},
            ]
        },
        headers=user["headers"],
    )

    assert resp.status_code == 409
    assert get_stock(ok) == 5
    with session_factory() as db:
        assert db.query(models.Order).count() == 0


def test_unexpected_error_triggers_rollback_and_propagates(
    client, make_user, make_product, monkeypatch
):
    user = make_user()
    pid = make_product()

    def boom(*args, **kwargs):
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(order_service, "create_order", boom)
    with pytest.raises(RuntimeError):
        client.post(
            "/orders/",
            json={"items": [{"product_id": pid, "quantity": 1}]},
            headers=user["headers"],
        )


# --- Pruebas unitarias directas del servicio ---


def _db_user(db):
    user = models.User(name="Ana", email="ana@correo.com", hashed_password="x")
    db.add(user)
    db.commit()
    return user


def test_service_raises_product_not_found(session_factory):
    with session_factory() as db:
        user = _db_user(db)
        data = schemas.OrderCreate(items=[{"product_id": 999, "quantity": 1}])
        with pytest.raises(order_service.ProductNotFoundError) as exc:
            order_service.create_order(db, user, data)
        assert exc.value.product_id == 999


def test_service_raises_insufficient_stock(session_factory):
    with session_factory() as db:
        user = _db_user(db)
        product = models.Product(name="P", price=Decimal("10.00"), stock=1)
        db.add(product)
        db.commit()
        data = schemas.OrderCreate(items=[{"product_id": product.id, "quantity": 2}])
        with pytest.raises(order_service.InsufficientStockError) as exc:
            order_service.create_order(db, user, data)
        assert exc.value.available == 1
        assert exc.value.product_name == "P"