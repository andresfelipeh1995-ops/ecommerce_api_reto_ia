from datetime import datetime

from app import models


def _set_order(session_factory, order_id, **fields):
    with session_factory() as db:
        order = db.get(models.Order, order_id)
        for key, value in fields.items():
            setattr(order, key, value)
        db.commit()


def test_history_requires_authentication(client):
    assert client.get("/users/1/orders").status_code == 401


def test_history_empty(client, make_user):
    user = make_user()
    resp = client.get(f"/users/{user['id']}/orders", headers=user["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_history_includes_product_names(client, make_user, make_product, place_order):
    user = make_user()
    keyboard = make_product(name="Teclado", price="50.00")
    mouse = make_product(name="Mouse", price="20.00")
    place_order(
        user["headers"],
        [{"product_id": keyboard, "quantity": 1}, {"product_id": mouse, "quantity": 2}],
    )

    resp = client.get(f"/users/{user['id']}/orders", headers=user["headers"])

    assert resp.status_code == 200
    orders = resp.json()
    assert len(orders) == 1
    names = {item["product_name"] for item in orders[0]["items"]}
    assert names == {"Teclado", "Mouse"}


def test_user_cannot_see_other_users_history(client, make_user):
    ana = make_user(email="ana@correo.com")
    luis = make_user(email="luis@correo.com", name="Luis")
    resp = client.get(f"/users/{luis['id']}/orders", headers=ana["headers"])
    assert resp.status_code == 403


def test_admin_can_see_any_history(client, make_user, make_product, place_order):
    ana = make_user(email="ana@correo.com")
    admin = make_user(email="admin@correo.com", name="Admin", admin=True)
    pid = make_product()
    place_order(ana["headers"], [{"product_id": pid, "quantity": 1}])

    resp = client.get(f"/users/{ana['id']}/orders", headers=admin["headers"])

    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_history_of_nonexistent_user_returns_404(client, make_user):
    admin = make_user(email="admin@correo.com", admin=True)
    resp = client.get("/users/9999/orders", headers=admin["headers"])
    assert resp.status_code == 404


def test_history_only_returns_own_orders(client, make_user, make_product, place_order):
    ana = make_user(email="ana@correo.com")
    luis = make_user(email="luis@correo.com", name="Luis")
    pid = make_product()
    place_order(ana["headers"], [{"product_id": pid, "quantity": 1}])
    place_order(luis["headers"], [{"product_id": pid, "quantity": 1}])

    resp = client.get(f"/users/{ana['id']}/orders", headers=ana["headers"])

    assert len(resp.json()) == 1


def test_history_pagination_and_order(client, make_user, make_product, place_order):
    user = make_user()
    pid = make_product(stock=10)
    ids = [
        place_order(user["headers"], [{"product_id": pid, "quantity": 1}])["id"]
        for _ in range(3)
    ]
    url = f"/users/{user['id']}/orders"

    page1 = client.get(url, params={"limit": 2, "offset": 0}, headers=user["headers"]).json()
    page2 = client.get(url, params={"limit": 2, "offset": 2}, headers=user["headers"]).json()

    # Más reciente primero
    assert [o["id"] for o in page1] == [ids[2], ids[1]]
    assert [o["id"] for o in page2] == [ids[0]]


def test_history_filter_by_status(client, make_user, make_product, place_order, session_factory):
    user = make_user()
    pid = make_product(stock=10)
    first = place_order(user["headers"], [{"product_id": pid, "quantity": 1}])
    place_order(user["headers"], [{"product_id": pid, "quantity": 1}])
    _set_order(session_factory, first["id"], status=models.OrderStatus.PAID)
    url = f"/users/{user['id']}/orders"

    paid = client.get(url, params={"status": "paid"}, headers=user["headers"]).json()
    pending = client.get(url, params={"status": "pending"}, headers=user["headers"]).json()

    assert [o["id"] for o in paid] == [first["id"]]
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


def test_history_filter_by_dates(client, make_user, make_product, place_order, session_factory):
    user = make_user()
    pid = make_product(stock=10)
    jan = place_order(user["headers"], [{"product_id": pid, "quantity": 1}])
    mar = place_order(user["headers"], [{"product_id": pid, "quantity": 1}])
    _set_order(session_factory, jan["id"], created_at=datetime(2026, 1, 10))
    _set_order(session_factory, mar["id"], created_at=datetime(2026, 3, 10))
    url = f"/users/{user['id']}/orders"

    since = client.get(
        url, params={"date_from": "2026-02-01T00:00:00"}, headers=user["headers"]
    ).json()
    until = client.get(
        url, params={"date_to": "2026-02-01T00:00:00"}, headers=user["headers"]
    ).json()
    between = client.get(
        url,
        params={"date_from": "2026-01-01T00:00:00", "date_to": "2026-12-31T00:00:00"},
        headers=user["headers"],
    ).json()

    assert [o["id"] for o in since] == [mar["id"]]
    assert [o["id"] for o in until] == [jan["id"]]
    assert len(between) == 2


def test_history_rejects_inverted_date_range(client, make_user):
    user = make_user()
    resp = client.get(
        f"/users/{user['id']}/orders",
        params={"date_from": "2026-12-01T00:00:00", "date_to": "2026-01-01T00:00:00"},
        headers=user["headers"],
    )
    assert resp.status_code == 422


def test_history_rejects_invalid_params(client, make_user):
    user = make_user()
    url = f"/users/{user['id']}/orders"
    assert client.get(url, params={"status": "inventado"}, headers=user["headers"]).status_code == 422
    assert client.get(url, params={"limit": 0}, headers=user["headers"]).status_code == 422
    assert client.get(url, params={"offset": -1}, headers=user["headers"]).status_code == 422