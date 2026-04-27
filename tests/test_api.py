from datetime import datetime, timedelta


def _auth_header(client, username="admin", password="admin123"):
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_product_context(client, headers, sku="SKU-T1"):
    wh = client.post(
        "/warehouses",
        json={"name": f"Warehouse-{sku}", "location": "Durban"},
        headers=headers,
    )
    assert wh.status_code == 200
    wh_id = wh.json()["id"]

    product = client.post(
        "/products",
        json={
            "sku": sku,
            "name": "Widget",
            "warehouse_id": wh_id,
            "quantity_on_hand": 0,
        },
        headers=headers,
    )
    assert product.status_code == 200
    return product.json()["id"]


def test_auth_token_login_success(client):
    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["role"] == "admin"
    assert payload["access_token"]


def test_role_guards_for_stock_movements(client):
    product_id = _create_product_context(client, _auth_header(client, "admin", "admin123"), "SKU-T2")

    unauth = client.get("/stock-movements")
    assert unauth.status_code == 401

    clerk_headers = _auth_header(client, "clerk", "clerk123")
    clerk_get = client.get("/stock-movements", headers=clerk_headers)
    assert clerk_get.status_code == 200

    clerk_post = client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "IN", "quantity": 1, "note": "forbidden"},
        headers=clerk_headers,
    )
    assert clerk_post.status_code == 403


def test_fifo_consumption_behavior(client):
    headers = _auth_header(client, "admin", "admin123")
    product_id = _create_product_context(client, headers, "SKU-T3")

    in1 = client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "IN", "quantity": 3, "note": "lot1"},
        headers=headers,
    )
    assert in1.status_code == 200
    in2 = client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "IN", "quantity": 5, "note": "lot2"},
        headers=headers,
    )
    assert in2.status_code == 200

    out = client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "OUT", "quantity": 4, "note": "dispatch"},
        headers=headers,
    )
    assert out.status_code == 200

    products = client.get("/products", headers=headers)
    assert products.status_code == 200
    created = [p for p in products.json() if p["id"] == product_id][0]
    assert created["quantity_on_hand"] == 4

    lots = client.get(f"/products/{product_id}/lots", headers=headers)
    assert lots.status_code == 200
    lot_rows = lots.json()
    assert lot_rows[0]["quantity_remaining"] == 0
    assert lot_rows[1]["quantity_remaining"] == 4


def test_audit_fields_and_filters(client):
    headers = _auth_header(client, "admin", "admin123")
    product_id = _create_product_context(client, headers, "SKU-T4")

    move = client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "IN", "quantity": 2, "note": "audit in"},
        headers=headers,
    )
    assert move.status_code == 200
    assert move.json()["performed_by"] == "admin"

    filtered = client.get(f"/stock-movements?product_id={product_id}", headers=headers)
    assert filtered.status_code == 200
    assert len(filtered.json()) >= 1
    assert all(m["product_id"] == product_id for m in filtered.json())

    now = datetime.utcnow()
    start = (now - timedelta(minutes=1)).isoformat()
    end = (now + timedelta(minutes=1)).isoformat()
    by_date = client.get(
        f"/stock-movements?product_id={product_id}&date_from={start}&date_to={end}",
        headers=headers,
    )
    assert by_date.status_code == 200
    assert len(by_date.json()) >= 1
