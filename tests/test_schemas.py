import pytest
from pydantic import ValidationError

from app import schemas


def test_user_create_valid():
    user = schemas.UserCreate(name="Ana", email="ana@correo.com", password="Clave12345")
    assert user.email == "ana@correo.com"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Ana", "email": "no-es-email", "password": "Clave12345"},
        {"name": "Ana", "email": "ana@correo.com", "password": "corta"},
        {"name": "A", "email": "ana@correo.com", "password": "Clave12345"},
        {"name": "Ana", "email": "ana@correo.com", "password": "x" * 73},
    ],
)
def test_user_create_invalid(payload):
    with pytest.raises(ValidationError):
        schemas.UserCreate(**payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "P", "price": "0", "stock": 1},
        {"name": "P", "price": "-5", "stock": 1},
        {"name": "P", "price": "10", "stock": -1},
        {"name": "", "price": "10", "stock": 1},
    ],
)
def test_product_create_invalid(payload):
    with pytest.raises(ValidationError):
        schemas.ProductCreate(**payload)


def test_order_create_valid():
    order = schemas.OrderCreate(items=[{"product_id": 1, "quantity": 2}])
    assert order.items[0].quantity == 2


def test_order_create_rejects_empty_items():
    with pytest.raises(ValidationError):
        schemas.OrderCreate(items=[])


def test_order_create_rejects_duplicates():
    with pytest.raises(ValidationError):
        schemas.OrderCreate(
            items=[{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 2}]
        )


@pytest.mark.parametrize("quantity", [0, -1, 101])
def test_order_item_rejects_invalid_quantity(quantity):
    with pytest.raises(ValidationError):
        schemas.OrderItemIn(product_id=1, quantity=quantity)