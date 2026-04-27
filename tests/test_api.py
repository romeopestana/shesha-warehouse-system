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


def test_stock_transfer_success_and_fifo_effect(client):
    headers = _auth_header(client, "admin", "admin123")

    wh_a = client.post(
        "/warehouses",
        json={"name": "Warehouse-A", "location": "Durban"},
        headers=headers,
    )
    assert wh_a.status_code == 200
    wh_b = client.post(
        "/warehouses",
        json={"name": "Warehouse-B", "location": "Cape Town"},
        headers=headers,
    )
    assert wh_b.status_code == 200

    source = client.post(
        "/products",
        json={
            "sku": "SKU-T5-SRC",
            "name": "Source Product",
            "warehouse_id": wh_a.json()["id"],
            "quantity_on_hand": 0,
        },
        headers=headers,
    )
    assert source.status_code == 200
    destination = client.post(
        "/products",
        json={
            "sku": "SKU-T5-DST",
            "name": "Destination Product",
            "warehouse_id": wh_b.json()["id"],
            "quantity_on_hand": 0,
        },
        headers=headers,
    )
    assert destination.status_code == 200

    source_id = source.json()["id"]
    destination_id = destination.json()["id"]

    assert (
        client.post(
            "/stock-movements",
            json={"product_id": source_id, "movement_type": "IN", "quantity": 3, "note": "lot1"},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/stock-movements",
            json={"product_id": source_id, "movement_type": "IN", "quantity": 5, "note": "lot2"},
            headers=headers,
        ).status_code
        == 200
    )

    transfer = client.post(
        "/stock-transfers",
        json={
            "source_product_id": source_id,
            "destination_product_id": destination_id,
            "quantity": 4,
            "note": "inter-warehouse",
        },
        headers=headers,
    )
    assert transfer.status_code == 200
    payload = transfer.json()
    assert payload["performed_by"] == "admin"
    assert payload["source_product_id"] == source_id
    assert payload["destination_product_id"] == destination_id

    products = client.get("/products", headers=headers).json()
    source_row = [p for p in products if p["id"] == source_id][0]
    destination_row = [p for p in products if p["id"] == destination_id][0]
    assert source_row["quantity_on_hand"] == 4
    assert destination_row["quantity_on_hand"] == 4

    source_lots = client.get(f"/products/{source_id}/lots", headers=headers).json()
    assert source_lots[0]["quantity_remaining"] == 0
    assert source_lots[1]["quantity_remaining"] == 4

    destination_lots = client.get(f"/products/{destination_id}/lots", headers=headers).json()
    assert destination_lots[0]["quantity_remaining"] == 4


def test_stock_transfer_validations(client):
    admin_headers = _auth_header(client, "admin", "admin123")
    clerk_headers = _auth_header(client, "clerk", "clerk123")

    wh_a = client.post(
        "/warehouses",
        json={"name": "Warehouse-C", "location": "Durban"},
        headers=admin_headers,
    )
    wh_b = client.post(
        "/warehouses",
        json={"name": "Warehouse-D", "location": "Johannesburg"},
        headers=admin_headers,
    )
    assert wh_a.status_code == 200
    assert wh_b.status_code == 200

    p_same_wh_1 = client.post(
        "/products",
        json={
            "sku": "SKU-T6-A",
            "name": "Same WH 1",
            "warehouse_id": wh_a.json()["id"],
            "quantity_on_hand": 10,
        },
        headers=admin_headers,
    )
    p_same_wh_2 = client.post(
        "/products",
        json={
            "sku": "SKU-T6-B",
            "name": "Same WH 2",
            "warehouse_id": wh_a.json()["id"],
            "quantity_on_hand": 0,
        },
        headers=admin_headers,
    )
    p_other_wh = client.post(
        "/products",
        json={
            "sku": "SKU-T6-C",
            "name": "Other WH",
            "warehouse_id": wh_b.json()["id"],
            "quantity_on_hand": 0,
        },
        headers=admin_headers,
    )
    assert p_same_wh_1.status_code == 200
    assert p_same_wh_2.status_code == 200
    assert p_other_wh.status_code == 200

    clerk_forbidden = client.post(
        "/stock-transfers",
        json={
            "source_product_id": p_same_wh_1.json()["id"],
            "destination_product_id": p_other_wh.json()["id"],
            "quantity": 1,
            "note": "clerk should fail",
        },
        headers=clerk_headers,
    )
    assert clerk_forbidden.status_code == 403

    same_warehouse = client.post(
        "/stock-transfers",
        json={
            "source_product_id": p_same_wh_1.json()["id"],
            "destination_product_id": p_same_wh_2.json()["id"],
            "quantity": 1,
            "note": "same warehouse should fail",
        },
        headers=admin_headers,
    )
    assert same_warehouse.status_code == 400

    insufficient = client.post(
        "/stock-transfers",
        json={
            "source_product_id": p_same_wh_1.json()["id"],
            "destination_product_id": p_other_wh.json()["id"],
            "quantity": 999,
            "note": "too much",
        },
        headers=admin_headers,
    )
    assert insufficient.status_code == 400


def test_stock_transfer_list_filters_and_roles(client):
    admin_headers = _auth_header(client, "admin", "admin123")
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
    assert wh_a.status_code == 200
    assert wh_b.status_code == 200

    source = client.post(
        "/products",
        json={
            "sku": "SKU-T7-SRC",
            "name": "Filter Source",
            "warehouse_id": wh_a.json()["id"],
            "quantity_on_hand": 10,
        },
        headers=admin_headers,
    )
    destination = client.post(
        "/products",
        json={
            "sku": "SKU-T7-DST",
            "name": "Filter Destination",
            "warehouse_id": wh_b.json()["id"],
            "quantity_on_hand": 0,
        },
        headers=admin_headers,
    )
    assert source.status_code == 200
    assert destination.status_code == 200

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

    admin_list = client.get("/stock-transfers", headers=admin_headers)
    assert admin_list.status_code == 200
    assert len(admin_list.json()) >= 1

    clerk_list = client.get("/stock-transfers", headers=clerk_headers)
    assert clerk_list.status_code == 200
    assert len(clerk_list.json()) >= 1

    by_source = client.get(
        f"/stock-transfers?source_warehouse_id={wh_a.json()['id']}",
        headers=admin_headers,
    )
    assert by_source.status_code == 200
    assert all(t["source_warehouse_id"] == wh_a.json()["id"] for t in by_source.json())

    by_destination = client.get(
        f"/stock-transfers?destination_warehouse_id={wh_b.json()['id']}",
        headers=admin_headers,
    )
    assert by_destination.status_code == 200
    assert all(
        t["destination_warehouse_id"] == wh_b.json()["id"] for t in by_destination.json()
    )

    now = datetime.utcnow()
    start = (now - timedelta(minutes=1)).isoformat()
    end = (now + timedelta(minutes=1)).isoformat()
    by_date = client.get(
        f"/stock-transfers?date_from={start}&date_to={end}",
        headers=admin_headers,
    )
    assert by_date.status_code == 200
    assert len(by_date.json()) >= 1
