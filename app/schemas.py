"""Esquemas Pydantic: validan la entrada y definen la forma de las respuestas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ErrorOut(BaseModel):
    """Formato estándar de error de la API."""

    detail: str = Field(
        description="Mensaje que explica el error",
        examples=["Producto 5 no existe"],
    )


# ---------- Usuarios y autenticación ----------


class UserCreate(BaseModel):
    """Datos para registrar un usuario nuevo."""

    name: str = Field(
        min_length=2, max_length=50, description="Nombre del usuario", examples=["Ana Pérez"]
    )
    email: EmailStr = Field(description="Correo electrónico único", examples=["ana@correo.com"])
    password: str = Field(
        min_length=8,
        max_length=72,
        description="Contraseña (8 a 72 caracteres, límite de bcrypt)",
        examples=["Clave12345"],
    )


class UserOut(BaseModel):
    """Usuario tal como se devuelve al cliente. Nunca incluye la contraseña."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del usuario", examples=[1])
    name: str = Field(description="Nombre del usuario", examples=["Ana Pérez"])
    email: EmailStr = Field(description="Correo electrónico", examples=["ana@correo.com"])


class Token(BaseModel):
    """Token de acceso JWT."""

    access_token: str = Field(description="JWT firmado; se envía en el header Authorization")
    token_type: str = Field(default="bearer", description="Tipo de token", examples=["bearer"])


# ---------- Productos ----------


class ProductCreate(BaseModel):
    """Datos para crear un producto."""

    name: str = Field(
        min_length=1, max_length=100, description="Nombre del producto", examples=["Teclado mecánico"]
    )
    price: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Precio unitario (mayor que 0, hasta 2 decimales)",
        examples=["99.90"],
    )
    stock: int = Field(ge=0, description="Unidades disponibles en inventario", examples=[25])


class ProductOut(ProductCreate):
    """Producto tal como se devuelve al cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del producto", examples=[3])


# ---------- Pedidos ----------


class OrderItemIn(BaseModel):
    """Una línea del pedido: producto y cantidad."""

    product_id: int = Field(description="Id del producto a comprar", examples=[3])
    quantity: int = Field(gt=0, le=100, description="Unidades (1 a 100)", examples=[2])


class OrderCreate(BaseModel):
    """Datos para crear un pedido."""

    items: list[OrderItemIn] = Field(
        min_length=1,
        max_length=50,
        description="Líneas del pedido (1 a 50, sin productos repetidos)",
        examples=[[{"product_id": 3, "quantity": 2}, {"product_id": 7, "quantity": 1}]],
    )

    @field_validator("items")
    @classmethod
    def no_duplicates(cls, items: list[OrderItemIn]) -> list[OrderItemIn]:
        """Rechaza pedidos con el mismo producto en más de una línea."""
        ids = [item.product_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Productos duplicados en el pedido")
        return items


class OrderItemOut(BaseModel):
    """Línea de un pedido ya registrado."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int = Field(description="Id del producto", examples=[3])
    product_name: str = Field(description="Nombre del producto", examples=["Teclado mecánico"])
    quantity: int = Field(description="Unidades compradas", examples=[2])
    unit_price: Decimal = Field(
        description="Precio unitario cobrado, con descuento aplicado", examples=["180.00"]
    )


class OrderOut(BaseModel):
    """Pedido registrado con sus líneas."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del pedido", examples=[7])
    total_price: Decimal = Field(description="Total del pedido", examples=["360.00"])
    status: str = Field(
        description="Estado: pending, paid o cancelled", examples=["pending"]
    )
    created_at: datetime = Field(description="Fecha de creación (UTC)")
    items: list[OrderItemOut] = Field(description="Productos comprados")