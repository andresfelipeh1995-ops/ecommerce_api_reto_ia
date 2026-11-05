"""Llena la base de datos con datos de demostración.

Uso:
    python seed.py

Es idempotente: si los usuarios o productos ya existen, no los duplica.
"""

from decimal import Decimal

from app import models, schemas
from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.services.order_service import create_order

USERS = [
    {"name": "Admin Demo", "email": "admin@shop.com", "password": "Admin12345", "is_admin": True},
    {"name": "Ana Pérez", "email": "ana@correo.com", "password": "Clave12345", "is_admin": False},
    {"name": "Luis Gómez", "email": "luis@correo.com", "password": "Clave12345", "is_admin": False},
]

PRODUCTS = [
    {"name": "Teclado mecánico", "price": "180.00", "stock": 25},
    {"name": "Mouse inalámbrico", "price": "45.90", "stock": 50},
    {"name": 'Monitor 27"', "price": "320.00", "stock": 15},
    {"name": "Auriculares Bluetooth", "price": "89.99", "stock": 40},
    {"name": "Webcam HD", "price": "65.50", "stock": 30},
    {"name": "Silla ergonómica", "price": "250.00", "stock": 8},
    {"name": "Hub USB-C", "price": "35.00", "stock": 60},
    {"name": "Disco SSD 1TB", "price": "120.00", "stock": 20},
    {"name": "Soporte para laptop", "price": "55.00", "stock": 35},
    {"name": "Micrófono USB", "price": "140.00", "stock": 12},
]

# email -> lista de pedidos; cada pedido es (estado, [(nombre_producto, cantidad)])
ORDERS = {
    "ana@correo.com": [
        ("paid", [("Teclado mecánico", 2), ("Mouse inalámbrico", 1)]),
        ("pending", [('Monitor 27"', 1)]),
    ],
    "luis@correo.com": [
        ("pending", [("Hub USB-C", 3)]),
    ],
}


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    users_by_email: dict[str, models.User] = {}
    created_users = 0
    for data in USERS:
        user = db.query(models.User).filter(models.User.email == data["email"]).first()
        if user is None:
            user = models.User(
                name=data["name"],
                email=data["email"],
                hashed_password=hash_password(data["password"]),
                is_admin=data["is_admin"],
            )
            db.add(user)
            created_users += 1
        else:
            user.is_admin = data["is_admin"]
        users_by_email[data["email"]] = user

    products_by_name: dict[str, models.Product] = {}
    created_products = 0
    for data in PRODUCTS:
        product = db.query(models.Product).filter(models.Product.name == data["name"]).first()
        if product is None:
            product = models.Product(
                name=data["name"],
                price=Decimal(data["price"]),
                stock=data["stock"],
            )
            db.add(product)
            created_products += 1
        products_by_name[data["name"]] = product

    db.commit()
    for user in users_by_email.values():
        db.refresh(user)

    created_orders = 0
    for email, orders in ORDERS.items():
        user = users_by_email[email]
        has_orders = db.query(models.Order).filter(models.Order.user_id == user.id).first()
        if has_orders is not None:
            continue
        for order_status, items in orders:
            payload = schemas.OrderCreate(
                items=[
                    schemas.OrderItemIn(
                        product_id=products_by_name[name].id,
                        quantity=quantity,
                    )
                    for name, quantity in items
                ]
            )
            order = create_order(db, user, payload)
            order.status = models.OrderStatus(order_status)
            db.commit()
            created_orders += 1

    total_users = db.query(models.User).count()
    total_products = db.query(models.Product).count()
    total_orders = db.query(models.Order).count()
    db.close()

    print("Base de datos lista:")
    print(f"  usuarios : {total_users} (nuevos: {created_users})")
    print(f"  productos: {total_products} (nuevos: {created_products})")
    print(f"  pedidos  : {total_orders} (nuevos: {created_orders})")
    print()
    print("Credenciales de prueba:")
    for data in USERS:
        role = "admin" if data["is_admin"] else "usuario"
        print(f"  [{role:7}] {data['email']} / {data['password']}")


if __name__ == "__main__":
    main()
