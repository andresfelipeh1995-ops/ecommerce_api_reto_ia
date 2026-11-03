from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401  (registra las tablas para create_all)
from app.config import settings
from app.database import Base, engine
from app.limiter import limiter
from app.routers import auth, orders, products, users

Base.metadata.create_all(bind=engine)

DESCRIPTION = """
API REST de comercio electrónico.

## Cómo autenticarse
1. Registra un usuario con `POST /users/`.
2. Inicia sesión con `POST /auth/login` y copia el `access_token`.
3. Pulsa **Authorize** (arriba a la derecha) y pega el token.

## Reglas de negocio
* Los productos con precio mayor al umbral configurado reciben un descuento porcentual.
* Al crear un pedido se valida y descuenta el stock de forma atómica.
* Un usuario solo puede ver su propio historial; un administrador puede ver el de cualquiera.

## Errores
Los errores devuelven `{"detail": "mensaje"}` con el código HTTP correspondiente.
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Inicio de sesión y emisión de tokens JWT."},
    {"name": "users", "description": "Registro de usuarios, perfil e historial de pedidos."},
    {"name": "products", "description": "Catálogo de productos con paginación."},
    {"name": "orders", "description": "Creación de pedidos con control de stock."},
]

app = FastAPI(
    title="E-commerce API",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS_METADATA,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Oculta los detalles internos de la base de datos al cliente."""
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)