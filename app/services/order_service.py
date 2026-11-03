from decimal import Decimal

from sqlalchemy.orm import Session
from datetime import datetime

from sqlalchemy.orm import selectinload
from app import models
from app import schemas
from app.services.pricing import final_unit_price


class ProductNotFoundError(Exception):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"Producto {product_id} no existe")
        self.product_id = product_id


class InsufficientStockError(Exception):
    def __init__(self, product_name: str, available: int) -> None:
        super().__init__(f"Stock insuficiente para '{product_name}'")
        self.product_name = product_name
        self.available = available


def create_order(db: Session, user: models.User, data: schemas.OrderCreate) -> models.Order:
    """Crea el pedido bloqueando filas de productos para evitar sobreventa.

    No hace commit: la transacción la controla el router.
    """
    ids = sorted(item.product_id for item in data.items)  # orden fijo evita deadlocks
    products = (
        db.query(models.Product)
        .filter(models.Product.id.in_(ids))  # una sola consulta (sin N+1)
        .order_by(models.Product.id)
        .with_for_update()
        .all()
    )
    by_id = {product.id: product for product in products}

    order = models.Order(user_id=user.id, total_price=Decimal("0"))
    total = Decimal("0")

    for item in data.items:
        product = by_id.get(item.product_id)
        if product is None:
            raise ProductNotFoundError(item.product_id)
        if product.stock < item.quantity:
            raise InsufficientStockError(product.name, product.stock)

        unit_price = final_unit_price(product.price)
        product.stock -= item.quantity
        total += unit_price * item.quantity
        order.items.append(
            models.OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=unit_price,
            )
        )

    order.total_price = total
    db.add(order)
    return order

def list_user_orders(
    db: Session,
    user_id: int,
    *,
    status: models.OrderStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[models.Order]:
    """Historial de pedidos de un usuario, del más reciente al más antiguo."""
    query = (
        db.query(models.Order)
        .options(
            # Carga items y productos en 2 consultas extra (evita N+1)
            selectinload(models.Order.items).selectinload(models.OrderItem.product)
        )
        .filter(models.Order.user_id == user_id)
    )
    if status is not None:
        query = query.filter(models.Order.status == status)
    if date_from is not None:
        query = query.filter(models.Order.created_at >= date_from)
    if date_to is not None:
        query = query.filter(models.Order.created_at <= date_to)

    return (
        query.order_by(models.Order.created_at.desc(), models.Order.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )