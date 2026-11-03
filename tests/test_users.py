from app.limiter import limiter

from tests.conftest import PASSWORD


def test_create_user_returns_201_without_password(client):
    resp = client.post(
        "/users/", json={"name": "Ana", "email": "ana@correo.com", "password": PASSWORD}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "ana@correo.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_duplicate_email_returns_409(client):
    payload = {"name": "Ana", "email": "ana@correo.com", "password": PASSWORD}
    assert client.post("/users/", json=payload).status_code == 201
    assert client.post("/users/", json=payload).status_code == 409


def test_invalid_email_returns_422(client):
    resp = client.post(
        "/users/", json={"name": "Ana", "email": "malo", "password": PASSWORD}
    )
    assert resp.status_code == 422


def test_login_success(client, make_user):
    user = make_user()
    resp = client.post("/auth/login", data={"username": user["email"], "password": PASSWORD})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password(client, make_user):
    user = make_user()
    resp = client.post("/auth/login", data={"username": user["email"], "password": "incorrecta"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/auth/login", data={"username": "nadie@correo.com", "password": PASSWORD})
    assert resp.status_code == 401


def test_read_me(client, make_user):
    user = make_user()
    resp = client.get("/users/me", headers=user["headers"])
    assert resp.status_code == 200
    assert resp.json()["id"] == user["id"]


def test_login_is_rate_limited(client, make_user):
    make_user()
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            client.post(
                "/auth/login", data={"username": "ana@correo.com", "password": "mala"}
            ).status_code
            for _ in range(7)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert codes[:5] == [401] * 5
    assert 429 in codes[5:]