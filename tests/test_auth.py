from datetime import datetime, timedelta, timezone

import jwt

from app import auth
from app.config import settings


def test_hash_and_verify_password():
    hashed = auth.hash_password("Clave12345")
    assert hashed != "Clave12345"
    assert auth.verify_password("Clave12345", hashed)
    assert not auth.verify_password("otra-clave", hashed)


def test_create_access_token_contains_subject_and_expiry():
    token = auth.create_access_token(42)
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "42"
    assert "exp" in payload


def test_protected_endpoint_without_token(client):
    assert client.get("/users/me").status_code == 401


def test_invalid_token(client):
    resp = client.get("/users/me", headers={"Authorization": "Bearer basura"})
    assert resp.status_code == 401


def test_expired_token(client):
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_token_with_non_numeric_subject(client):
    token = jwt.encode({"sub": "abc"}, settings.secret_key, algorithm=settings.algorithm)
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_for_deleted_or_unknown_user(client):
    token = auth.create_access_token(9999)
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_signed_with_other_key_is_rejected(client):
    token = jwt.encode({"sub": "1"}, "otra-clave-" + "y" * 32, algorithm=settings.algorithm)
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_admin_endpoint_rejects_regular_user(client, make_user):
    user = make_user()
    resp = client.post(
        "/products/",
        json={"name": "X", "price": "10.00", "stock": 1},
        headers=user["headers"],
    )
    assert resp.status_code == 403