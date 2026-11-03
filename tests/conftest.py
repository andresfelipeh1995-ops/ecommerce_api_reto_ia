import os

# Deben definirse ANTES de importar la app (config.py lee el entorno al importarse)
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "clave-de-pruebas-" + "x" * 32
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'

from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.limiter import limiter  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "Clave12345"


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter.enabled = False
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(client, session_factory):
    """Registra un usuario, lo loguea y devuelve {'id', 'email', 'headers'}."""

    def _make(email="ana@correo.com", name="Ana", admin=False):
        resp = client.post(
            "/users/", json={"name": name, "email": email, "password": PASSWORD}
        )
        assert resp.status_code == 201, resp.text
        user_id = resp.json()["id"]

        if admin:
            with session_factory() as db:
                db.get(models.User, user_id).is_admin = True
                db.commit()

        login = client.post("/auth/login", data={"username": email, "password": PASSWORD})
        token = login.json()["access_token"]
        return {
            "id": user_id,
            "email": email,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    return _make


@pytest.fixture()
def make_product(session_factory):
    def _make(name="Producto", price="50.00", stock=10) -> int:
        with session_factory() as db:
            product = models.Product(name=name, price=Decimal(price), stock=stock)
            db.add(product)
            db.commit()
            return product.id

    return _make


@pytest.fixture()
def get_stock(session_factory):
    def _get(product_id: int) -> int:
        with session_factory() as db:
            return db.get(models.Product, product_id).stock

    return _get


@pytest.fixture()
def place_order(client):
    def _place(headers, items):
        resp = client.post("/orders/", json={"items": items}, headers=headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _place