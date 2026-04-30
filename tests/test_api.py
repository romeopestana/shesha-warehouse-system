from datetime import datetime, timedelta, timezone


def _auth_header(client, username="admin", password="admin123"):
    response = client.post("/auth/token", data={"username": username, "password": password})
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
        json={"sku": sku, "name": "Widget", "warehouse_id": wh_id, "quantity_on_hand": 0},
        headers=headers,
    )
    assert product.status_code == 200
    return product.json()["id"]


def test_auth_token_login_success(client):
    response = client.post("/auth/token", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["role"] == "admin"
    assert payload["access_token"]


def test_role_guards_for_stock_movements(client):
    product_id = _create_product_context(client, _auth_header(client), "SKU-T2")
    assert client.get("/stock-movements").status_code == 401

    clerk_headers = _auth_header(client, "clerk", "clerk123")
    assert client.get("/stock-movements", headers=clerk_headers).status_code == 200
    clerk_post = client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "IN", "quantity": 1, "note": "forbidden"},
        headers=clerk_headers,
    )
    assert clerk_post.status_code == 403


def test_fifo_consumption_behavior(client):
    headers = _auth_header(client)
    product_id = _create_product_context(client, headers, "SKU-T3")

    assert client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "IN", "quantity": 3, "note": "lot1"},
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "IN", "quantity": 5, "note": "lot2"},
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/stock-movements",
        json={"product_id": product_id, "movement_type": "OUT", "quantity": 4, "note": "dispatch"},
        headers=headers,
    ).status_code == 200

    products = client.get("/products", headers=headers).json()
    created = [p for p in products if p["id"] == product_id][0]
    assert created["quantity_on_hand"] == 4

    lots = client.get(f"/products/{product_id}/lots", headers=headers).json()
    assert lots[0]["quantity_remaining"] == 0
    assert lots[1]["quantity_remaining"] == 4


def test_audit_fields_and_filters(client):
    headers = _auth_header(client)
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
    assert all(m["product_id"] == product_id for m in filtered.json())

    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    by_date = client.get(
        f"/stock-movements?product_id={product_id}&date_from={start}&date_to={end}",
        headers=headers,
    )
    assert by_date.status_code == 200
    assert len(by_date.json()) >= 1


def test_stock_transfer_list_filters_and_roles(client):
    admin_headers = _auth_header(client)
    clerk_headers = _auth_header(client, "clerk", "clerk123")

    wh_a = client.post(
        "/warehouses",
        json={"name": "Warehouse-E", "location": "Pretoria"},
        headers=admin_headers,
    )
    wh_b = client.post(
        "/warehouses",
        json={"name": "Warehouse-F", "location": "Port Elizabeth"},
        headers=admin_headers,
    )
    source = client.post(
        "/products",
        json={"sku": "SKU-T7-SRC", "name": "Filter Source", "warehouse_id": wh_a.json()["id"], "quantity_on_hand": 10},
        headers=admin_headers,
    )
    destination = client.post(
        "/products",
        json={"sku": "SKU-T7-DST", "name": "Filter Destination", "warehouse_id": wh_b.json()["id"], "quantity_on_hand": 0},
        headers=admin_headers,
    )
    assert source.status_code == 200 and destination.status_code == 200

    created = client.post(
        "/stock-transfers",
        json={
            "source_product_id": source.json()["id"],
            "destination_product_id": destination.json()["id"],
            "quantity": 2,
            "note": "filterable transfer",
        },
        headers=admin_headers,
    )
    assert created.status_code == 200
    assert client.get("/stock-transfers", headers=admin_headers).status_code == 200
    assert client.get("/stock-transfers", headers=clerk_headers).status_code == 200


def test_low_stock_alerts_with_warehouse_filter(client):
    admin_headers = _auth_header(client)
    clerk_headers = _auth_header(client, "clerk", "clerk123")

    wh_1 = client.post(
        "/warehouses",
        json={"name": "Warehouse-G", "location": "Durban"},
        headers=admin_headers,
    )
    wh_2 = client.post(
        "/warehouses",
        json={"name": "Warehouse-H", "location": "Cape Town"},
        headers=admin_headers,
    )
    low = client.post(
        "/products",
        json={
            "sku": "SKU-T8-LOW",
            "name": "Low Stock Product",
            "warehouse_id": wh_1.json()["id"],
            "quantity_on_hand": 2,
            "reorder_level": 5,
            "reorder_quantity": 20,
        },
        headers=admin_headers,
    )
    healthy = client.post(
        "/products",
        json={
            "sku": "SKU-T8-OK",
            "name": "Healthy Product",
            "warehouse_id": wh_2.json()["id"],
            "quantity_on_hand": 8,
            "reorder_level": 5,
            "reorder_quantity": 10,
        },
        headers=admin_headers,
    )
    assert low.status_code == 200 and healthy.status_code == 200

    by_admin = client.get("/alerts/low-stock", headers=admin_headers)
    assert by_admin.status_code == 200
    rows = by_admin.json()
    assert len(rows) >= 1
    assert all(r["quantity_on_hand"] <= r["reorder_level"] for r in rows)

    by_clerk = client.get("/alerts/low-stock", headers=clerk_headers)
    assert by_clerk.status_code == 200

    filtered = client.get(
        f"/alerts/low-stock?warehouse_id={wh_1.json()['id']}",
        headers=admin_headers,
    )
    assert filtered.status_code == 200
    assert all(r["warehouse_id"] == wh_1.json()["id"] for r in filtered.json())


def test_notifications_emission_and_read_flow(client):
    admin_headers = _auth_header(client)
    clerk_headers = _auth_header(client, "clerk", "clerk123")

    wh = client.post(
        "/warehouses",
        json={"name": "Warehouse-N", "location": "Welkom"},
        headers=admin_headers,
    )
    product = client.post(
        "/products",
        json={
            "sku": "SKU-T13-NOTIFY",
            "name": "Notify Product",
            "warehouse_id": wh.json()["id"],
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 3,
        },
        headers=admin_headers,
    )
    assert wh.status_code == 200 and product.status_code == 200

    assert client.get("/alerts/low-stock", headers=clerk_headers).status_code == 200
    notifications = client.get("/notifications?unread_only=true", headers=clerk_headers)
    assert notifications.status_code == 200
    rows = notifications.json()
    assert any(row["event_type"] == "low_stock_observed" for row in rows)

    first_id = rows[0]["id"]
    mark_read = client.post(f"/notifications/{first_id}/read", headers=clerk_headers)
    assert mark_read.status_code == 200
    assert mark_read.json()["is_read"] == 1


def test_low_stock_summary_endpoint(client):
    admin_headers = _auth_header(client)

    wh_a = client.post(
        "/warehouses",
        json={"name": "Summary Warehouse A", "location": "Vienna"},
        headers=admin_headers,
    )
    wh_b = client.post(
        "/warehouses",
        json={"name": "Summary Warehouse B", "location": "Graz"},
        headers=admin_headers,
    )
    assert wh_a.status_code == 200
    assert wh_b.status_code == 200

    low_a = client.post(
        "/products",
        json={
            "sku": "SUMMARY-LOW-A",
            "name": "Summary Low A",
            "warehouse_id": wh_a.json()["id"],
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 10,
        },
        headers=admin_headers,
    )
    low_b = client.post(
        "/products",
        json={
            "sku": "SUMMARY-LOW-B",
            "name": "Summary Low B",
            "warehouse_id": wh_b.json()["id"],
            "quantity_on_hand": 0,
            "reorder_level": 3,
            "reorder_quantity": 6,
        },
        headers=admin_headers,
    )
    healthy = client.post(
        "/products",
        json={
            "sku": "SUMMARY-OK",
            "name": "Summary Healthy",
            "warehouse_id": wh_b.json()["id"],
            "quantity_on_hand": 10,
            "reorder_level": 3,
            "reorder_quantity": 6,
        },
        headers=admin_headers,
    )
    assert low_a.status_code == 200
    assert low_b.status_code == 200
    assert healthy.status_code == 200

    summary = client.get("/alerts/summary", headers=admin_headers)
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["total_low_stock_items"] == 2
    assert len(payload["warehouse_breakdown"]) == 2
    assert any(row["warehouse_id"] == wh_a.json()["id"] and row["low_stock_count"] == 1 for row in payload["warehouse_breakdown"])
    assert any(row["warehouse_id"] == wh_b.json()["id"] and row["low_stock_count"] == 1 for row in payload["warehouse_breakdown"])
