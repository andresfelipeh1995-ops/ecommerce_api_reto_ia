from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth, models, responses, schemas
from app.database import get_db
from app.limiter import limiter
from app.services import order_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=schemas.UserOut,
    status_code=201,
    summary="Registrar usuario",
    response_description="Usuario creado (sin contraseña)",
    responses={409: responses.CONFLICT, 429: responses.RATE_LIMITED},
)
@limiter.limit("10/minute")
def create_user(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
) -> models.User:
    """Registra un usuario nuevo.

    - El email debe ser válido y **único**; si ya existe se responde `409`.
    - La contraseña se guarda cifrada con bcrypt y nunca se devuelve.
    - Los usuarios nuevos no son administradores.

    Límite: 10 registros por minuto por IP.
    """
    new_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=auth.hash_password(user.password),
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "El email ya está registrado") from None
    db.refresh(new_user)
    return new_user


@router.get(
    "/me",
    response_model=schemas.UserOut,
    summary="Ver mi perfil",
    response_description="Datos del usuario autenticado",
    responses={401: responses.UNAUTHORIZED},
)
def read_me(current_user: models.User = Depends(auth.get_current_user)) -> models.User:
    """Devuelve los datos del usuario dueño del token.

    Requiere autenticación.
    """
    return current_user


@router.get(
    "/{user_id}/orders",
    response_model=list[schemas.OrderOut],
    summary="Historial de pedidos de un usuario",
    response_description="Pedidos del usuario, del más reciente al más antiguo",
    responses={
        401: responses.UNAUTHORIZED,
        403: responses.FORBIDDEN,
        404: responses.NOT_FOUND,
    },
)
def list_user_orders(
    user_id: int,
    status: models.OrderStatus | None = Query(
        None, description="Filtrar por estado: pending, paid o cancelled"
    ),
    date_from: datetime | None = Query(
        None, description="Pedidos creados desde esta fecha (ISO 8601)", examples=["2026-11-01T00:00:00"]
    ),
    date_to: datetime | None = Query(
        None, description="Pedidos creados hasta esta fecha (ISO 8601)", examples=["2026-11-30T23:59:59"]
    ),
    limit: int = Query(20, ge=1, le=100, description="Máximo de pedidos a devolver"),
    offset: int = Query(0, ge=0, description="Cantidad de pedidos a saltar"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> list[models.Order]:
    """Devuelve el historial de pedidos de un usuario, con los nombres de los productos.

    **Autorización:** un usuario solo puede consultar su propio historial
    (`user_id` igual al del token). Un administrador puede consultar el de cualquiera.

    **Filtros opcionales:** `status`, `date_from` y `date_to`.
    **Paginación:** `limit` (1 a 100, por defecto 20) y `offset`.

    Errores: `403` si consulta a otro usuario sin ser admin, `404` si el usuario
    no existe y `422` si `date_from` es posterior a `date_to`.
    """
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(403, "No puedes ver los pedidos de otro usuario")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from no puede ser posterior a date_to")
    if db.get(models.User, user_id) is None:
        raise HTTPException(404, "Usuario no encontrado")

    return order_service.list_user_orders(
        db,
        user_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )