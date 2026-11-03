from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, models, responses, schemas
from app.database import get_db
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=schemas.Token,
    summary="Iniciar sesión",
    response_description="Token JWT de acceso",
    responses={401: responses.UNAUTHORIZED, 429: responses.RATE_LIMITED},
)
@limiter.limit("5/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    """Autentica a un usuario y devuelve un token JWT.

    Se envía como formulario (`application/x-www-form-urlencoded`), no como JSON:

    - **username**: el email con el que se registró el usuario.
    - **password**: la contraseña.

    El token devuelto se usa en el header `Authorization: Bearer <token>`.
    Límite: 5 intentos por minuto por IP (protección contra fuerza bruta).
    """
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if user is None or not auth.verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Email o contraseña incorrectos")
    return {"access_token": auth.create_access_token(user.id), "token_type": "bearer"}