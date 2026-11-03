def test_list_products_empty(client):
    resp = client.get("/products/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_products_pagination(client, make_product):
    ids = [make_product(name=f"P{i}") for i in range(5)]

    first = client.get("/products/", params={"limit": 2, "offset": 0}).json()
    second = client.get("/products/", params={"limit": 2, "offset": 2}).json()
    last = client.get("/products/", params={"limit": 2, "offset": 4}).json()

    assert [p["id"] for p in first] == ids[0:2]
    assert [p["id"] for p in second] == ids[2:4]
    assert [p["id"] for p in last] == ids[4:5]


def test_list_products_default_limit_is_20(client, make_product):
    for i in range(25):
        make_product(name=f"P{i}")
    assert len(client.get("/products/").json()) == 20


def test_offset_beyond_total_returns_empty(client, make_product):
    make_product()
    assert client.get("/products/", params={"offset": 50}).json() == []


def test_invalid_pagination_params(client):
    assert client.get("/products/", params={"limit": 0}).status_code == 422
    assert client.get("/products/", params={"limit": 101}).status_code == 422
    assert client.get("/products/", params={"offset": -1}).status_code == 422


def test_admin_can_create_product(client, make_user):
    admin = make_user(email="admin@correo.com", admin=True)
    resp = client.post(
        "/products/",
        json={"name": "Teclado", "price": "99.90", "stock": 5},
        headers=admin["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Teclado"
    assert len(client.get("/products/").json()) == 1


def test_create_product_requires_authentication(client):
    resp = client.post("/products/", json={"name": "X", "price": "10.00", "stock": 1})
    assert resp.status_code == 401


def test_create_product_validates_payload(client, make_user):
    admin = make_user(email="admin@correo.com", admin=True)
    resp = client.post(
        "/products/",
        json={"name": "X", "price": "-1", "stock": 1},
        headers=admin["headers"],
    )
    assert resp.status_code == 422