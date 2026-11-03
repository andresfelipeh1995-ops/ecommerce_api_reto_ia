from fastapi.routing import APIRoute

from app.main import app


def _api_routes():
    return [r for r in app.routes if isinstance(r, APIRoute)]


def test_every_endpoint_has_summary_tag_and_docstring():
    routes = _api_routes()
    assert routes, "No se encontraron endpoints"
    for route in routes:
        assert route.summary, f"{route.path} sin summary"
        assert route.tags, f"{route.path} sin tags"
        assert route.description.strip(), f"{route.path} sin docstring"


def test_openapi_metadata(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "E-commerce API"
    assert spec["info"]["description"]
    assert {t["name"] for t in spec["tags"]} == {"auth", "users", "products", "orders"}


def test_protected_endpoints_document_401(client):
    spec = client.get("/openapi.json").json()
    assert "401" in spec["paths"]["/orders/"]["post"]["responses"]
    assert "401" in spec["paths"]["/users/{user_id}/orders"]["get"]["responses"]
    assert "409" in spec["paths"]["/orders/"]["post"]["responses"]


def test_docs_pages_are_available(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200