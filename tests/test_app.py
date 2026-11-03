from unittest.mock import MagicMock

from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.main import app


def test_database_error_returns_generic_500(client):
    """Los errores de BD no deben filtrar detalles internos al cliente."""
    broken_db = MagicMock()
    broken_db.query.side_effect = SQLAlchemyError("detalle interno secreto")
    app.dependency_overrides[get_db] = lambda: broken_db

    resp = client.get("/products/")

    assert resp.status_code == 500
    assert resp.json() == {"detail": "Error interno del servidor"}
    assert "secreto" not in resp.text


def test_cors_allows_configured_origin(client):
    resp = client.options(
        "/products/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_blocks_unknown_origin(client):
    resp = client.options(
        "/products/",
        headers={
            "Origin": "http://sitio-malicioso.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in resp.headers


def test_openapi_documents_new_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/users/{user_id}/orders" in paths
    assert "/products/" in paths