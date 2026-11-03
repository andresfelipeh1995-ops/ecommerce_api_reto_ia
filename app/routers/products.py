from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import auth, models, responses, schemas
from app.database import get_db

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "/",
    response_model=list[schemas.ProductOut],
    summary="Listar productos",
    response_description="Página de productos ordenados por id",
)
def list_products(
    limit: int = Query(20, ge=1, le=100, description="Máximo de productos a devolver"),
    offset: int = Query(0, ge=0, description="Cantidad de productos a saltar"),
    db: Session = Depends(get_db),
) -> list[models.Product]:
    """Lista los productos del catálogo con paginación.

    Es un endpoint público (no requiere token).

    - `limit`: de 1 a 100, por defecto 20.
    - `offset`: desde 0. La página 2 de 10 en 10 es `limit=10&offset=10`.

    Si `offset` supera el total, se devuelve una lista vacía.
    """
    return (
        db.query(models.Product)
        .order_by(models.Product.id)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post(
    "/",
    response_model=schemas.ProductOut,
    status_code=201,
    summary="Crear producto",
    response_description="Producto creado",
    responses={401: responses.UNAUTHORIZED, 403: responses.FORBIDDEN},
)
def create_product(
    data: schemas.ProductCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.get_current_admin),
) -> models.Product:
    """Crea un producto en el catálogo.

    **Solo administradores.** El precio debe ser mayor que 0 y el stock no puede
    ser negativo.
    """
    product = models.Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product