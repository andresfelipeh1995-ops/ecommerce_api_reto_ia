from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, models, responses, schemas
from app.database import get_db
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/",
    response_model=schemas.OrderOut,
    status_code=201,
    summary="Crear pedido",
    response_description="Pedido creado con sus líneas y el total",
    responses={
        400: responses.BAD_REQUEST,
        401: responses.UNAUTHORIZED,
        409: responses.CONFLICT,
    },
)
def create_order(
    data: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> models.Order:
    """Crea un pedido para el usuario autenticado.

    El pedido siempre se asocia al usuario del token (no se envía `user_id`).

    **Reglas:**
    - Cada línea indica `product_id` y `quantity` (1 a 100); no se permiten productos repetidos.
    - Los productos con precio mayor al umbral configurado (por defecto 100) reciben
      un descuento porcentual (por defecto 10 %). El precio cobrado queda guardado
      en `unit_price`.
    - Se bloquean las filas de los productos y se valida el stock antes de descontarlo,
      para evitar sobreventa.
    - La operación es **atómica**: si una línea falla, no se descuenta stock de ninguna.

    **Errores:** `400` producto inexistente, `409` stock insuficiente,
    `401` sin token válido, `422` cuerpo inválido.
    """
    try:
        order = order_service.create_order(db, current_user, data)
        db.commit()
    except order_service.ProductNotFoundError as exc:
        db.rollback()
        raise HTTPException(400, f"El producto {exc.product_id} no existe") from None
    except order_service.InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(
            409, f"Stock insuficiente para '{exc.product_name}' (disponible: {exc.available})"
        ) from None
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    return order