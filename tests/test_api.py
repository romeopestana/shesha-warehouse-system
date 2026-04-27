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


def test_low_stock_alerts_with_warehouse_filter(client):
    admin_headers = _auth_header(client, "admin", "admin123")
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
    assert wh_1.status_code == 200
    assert wh_2.status_code == 200

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
    assert low.status_code == 200
    assert healthy.status_code == 200

    by_admin = client.get("/alerts/low-stock", headers=admin_headers)
    assert by_admin.status_code == 200
    rows = by_admin.json()
    assert len(rows) >= 1
    assert all(r["quantity_on_hand"] <= r["reorder_level"] for r in rows)
    low_row = [r for r in rows if r["product_id"] == low.json()["id"]][0]
    assert low_row["warehouse_id"] == wh_1.json()["id"]
    assert low_row["suggested_reorder"] == 20

    by_clerk = client.get("/alerts/low-stock", headers=clerk_headers)
    assert by_clerk.status_code == 200

    filtered = client.get(
        f"/alerts/low-stock?warehouse_id={wh_1.json()['id']}",
        headers=admin_headers,
    )
    assert filtered.status_code == 200
    assert all(r["warehouse_id"] == wh_1.json()["id"] for r in filtered.json())


def test_suggested_reorders_create_and_skip(client):
    admin_headers = _auth_header(client, "admin", "admin123")
    clerk_headers = _auth_header(client, "clerk", "clerk123")

    wh = client.post(
        "/warehouses",
        json={"name": "Warehouse-I", "location": "Bloemfontein"},
        headers=admin_headers,
    )
    assert wh.status_code == 200
    wh_id = wh.json()["id"]

    low_with_reorder = client.post(
        "/products",
        json={
            "sku": "SKU-T9-LOW-OK",
            "name": "Low With Reorder",
            "warehouse_id": wh_id,
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 10,
        },
        headers=admin_headers,
    )
    low_zero_reorder = client.post(
        "/products",
        json={
            "sku": "SKU-T9-LOW-SKIP",
            "name": "Low Zero Reorder",
            "warehouse_id": wh_id,
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 0,
        },
        headers=admin_headers,
    )
    healthy = client.post(
        "/products",
        json={
            "sku": "SKU-T9-HEALTHY",
            "name": "Healthy",
            "warehouse_id": wh_id,
            "quantity_on_hand": 9,
            "reorder_level": 5,
            "reorder_quantity": 10,
        },
        headers=admin_headers,
    )
    assert low_with_reorder.status_code == 200
    assert low_zero_reorder.status_code == 200
    assert healthy.status_code == 200

    forbidden = client.post(
        "/reorders/suggested",
        json={"warehouse_id": wh_id},
        headers=clerk_headers,
    )
    assert forbidden.status_code == 403

    result = client.post(
        "/reorders/suggested",
        json={
            "warehouse_id": wh_id,
            "product_ids": [
                low_with_reorder.json()["id"],
                low_zero_reorder.json()["id"],
                healthy.json()["id"],
            ],
            "note": "AUTO TEST REORDER",
        },
        headers=admin_headers,
    )
    assert result.status_code == 200
    payload = result.json()
    assert len(payload["created"]) == 1
    assert payload["created"][0]["product_id"] == low_with_reorder.json()["id"]
    assert payload["created"][0]["quantity_before"] == 1
    assert payload["created"][0]["quantity_after"] == 11
    assert len(payload["skipped"]) == 1
    assert payload["skipped"][0]["product_id"] == low_zero_reorder.json()["id"]

    movements = client.get(
        f"/stock-movements?product_id={low_with_reorder.json()['id']}",
        headers=admin_headers,
    )
    assert movements.status_code == 200
    assert any(m["note"] == "AUTO TEST REORDER" for m in movements.json())


def test_suggested_reorders_dry_run_no_persistence(client):
    admin_headers = _auth_header(client, "admin", "admin123")

    wh = client.post(
        "/warehouses",
        json={"name": "Warehouse-J", "location": "Polokwane"},
        headers=admin_headers,
    )
    assert wh.status_code == 200
    wh_id = wh.json()["id"]

    product = client.post(
        "/products",
        json={
            "sku": "SKU-T10-DRY",
            "name": "Dry Run Product",
            "warehouse_id": wh_id,
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 7,
        },
        headers=admin_headers,
    )
    assert product.status_code == 200
    product_id = product.json()["id"]

    preview = client.post(
        "/reorders/suggested",
        json={
            "warehouse_id": wh_id,
            "product_ids": [product_id],
            "note": "DRY RUN",
            "dry_run": True,
        },
        headers=admin_headers,
    )
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["proposal_id"] is not None
    assert len(payload["created"]) == 1
    assert payload["created"][0]["product_id"] == product_id
    assert payload["created"][0]["quantity_before"] == 1
    assert payload["created"][0]["quantity_after"] == 8

    products = client.get("/products", headers=admin_headers)
    assert products.status_code == 200
    row = [p for p in products.json() if p["id"] == product_id][0]
    assert row["quantity_on_hand"] == 1

    movements = client.get(f"/stock-movements?product_id={product_id}", headers=admin_headers)
    assert movements.status_code == 200
    assert all(m["note"] != "DRY RUN" for m in movements.json())


def test_reorder_proposal_approve_and_reject_flow(client):
    admin_headers = _auth_header(client, "admin", "admin123")
    clerk_headers = _auth_header(client, "clerk", "clerk123")

    wh = client.post(
        "/warehouses",
        json={"name": "Warehouse-K", "location": "Kimberley"},
        headers=admin_headers,
    )
    assert wh.status_code == 200
    wh_id = wh.json()["id"]

    p_approve = client.post(
        "/products",
        json={
            "sku": "SKU-T11-APP",
            "name": "Proposal Approve Product",
            "warehouse_id": wh_id,
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 6,
        },
        headers=admin_headers,
    )
    p_reject = client.post(
        "/products",
        json={
            "sku": "SKU-T11-REJ",
            "name": "Proposal Reject Product",
            "warehouse_id": wh_id,
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 4,
        },
        headers=admin_headers,
    )
    assert p_approve.status_code == 200
    assert p_reject.status_code == 200

    proposal_for_approve = client.post(
        "/reorders/suggested",
        json={
            "warehouse_id": wh_id,
            "product_ids": [p_approve.json()["id"]],
            "dry_run": True,
            "note": "APPROVE ME",
        },
        headers=admin_headers,
    )
    assert proposal_for_approve.status_code == 200
    assert proposal_for_approve.json()["proposal_id"] is not None

    # dry-run previews but should not mutate data before approval.
    products = client.get("/products", headers=admin_headers).json()
    before_row = [p for p in products if p["id"] == p_approve.json()["id"]][0]
    assert before_row["quantity_on_hand"] == 1

    proposals = client.get("/reorders/proposals?status=pending", headers=clerk_headers)
    assert proposals.status_code == 200
    pending = proposals.json()
    approve_proposal_id = pending[0]["id"]

    clerk_approve = client.post(
        f"/reorders/proposals/{approve_proposal_id}/approve",
        headers=clerk_headers,
    )
    assert clerk_approve.status_code == 403

    approved = client.post(
        f"/reorders/proposals/{approve_proposal_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["proposal"]["status"] == "approved"

    products_after_approve = client.get("/products", headers=admin_headers).json()
    approved_row = [p for p in products_after_approve if p["id"] == p_approve.json()["id"]][0]
    assert approved_row["quantity_on_hand"] == 7

    proposal_for_reject = client.post(
        "/reorders/suggested",
        json={
            "warehouse_id": wh_id,
            "product_ids": [p_reject.json()["id"]],
            "dry_run": True,
            "note": "REJECT ME",
        },
        headers=admin_headers,
    )
    assert proposal_for_reject.status_code == 200
    assert proposal_for_reject.json()["proposal_id"] is not None
    pending_after = client.get("/reorders/proposals?status=pending", headers=admin_headers)
    reject_proposal_id = pending_after.json()[0]["id"]

    rejected = client.post(
        f"/reorders/proposals/{reject_proposal_id}/reject",
        json={"reason": "Budget hold"},
        headers=admin_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Budget hold"

    reject_then_approve = client.post(
        f"/reorders/proposals/{reject_proposal_id}/approve",
        headers=admin_headers,
    )
    assert reject_then_approve.status_code == 400


def test_reorder_proposal_drift_checks_and_force_override(client):
    admin_headers = _auth_header(client, "admin", "admin123")

    wh_a = client.post(
        "/warehouses",
        json={"name": "Warehouse-L", "location": "Durban"},
        headers=admin_headers,
    )
    assert wh_a.status_code == 200

    p_drift = client.post(
        "/products",
        json={
            "sku": "SKU-T12-DRIFT",
            "name": "Drift Product",
            "warehouse_id": wh_a.json()["id"],
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 4,
        },
        headers=admin_headers,
    )
    p_force = client.post(
        "/products",
        json={
            "sku": "SKU-T12-FORCE",
            "name": "Force Product",
            "warehouse_id": wh_a.json()["id"],
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 3,
        },
        headers=admin_headers,
    )
    assert p_drift.status_code == 200
    assert p_force.status_code == 200

    proposal = client.post(
        "/reorders/suggested",
        json={
            "warehouse_id": wh_a.json()["id"],
            "product_ids": [p_drift.json()["id"], p_force.json()["id"]],
            "dry_run": True,
            "note": "DRIFT CHECK",
        },
        headers=admin_headers,
    )
    assert proposal.status_code == 200
    proposal_id = proposal.json()["proposal_id"]
    assert proposal_id is not None

    # product still exists but no longer low stock -> blocked unless force=true
    restock_force_product = client.post(
        "/stock-movements",
        json={
            "product_id": p_force.json()["id"],
            "movement_type": "IN",
            "quantity": 20,
            "note": "manual restock before approval",
        },
        headers=admin_headers,
    )
    assert restock_force_product.status_code == 200

    without_force = client.post(
        f"/reorders/proposals/{proposal_id}/approve",
        headers=admin_headers,
    )
    assert without_force.status_code == 200
    result = without_force.json()
    assert result["proposal"]["status"] == "approved"
    assert len(result["applied"]) == 1
    assert len(result["blocked"]) == 1
    assert result["blocked"][0]["reason"] == "product is no longer low-stock"

    p_force_only = client.post(
        "/products",
        json={
            "sku": "SKU-T12-FORCE-ONLY",
            "name": "Force Only Product",
            "warehouse_id": wh_a.json()["id"],
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 2,
        },
        headers=admin_headers,
    )
    assert p_force_only.status_code == 200

    proposal_force = client.post(
        "/reorders/suggested",
        json={
            "warehouse_id": wh_a.json()["id"],
            "product_ids": [p_force_only.json()["id"]],
            "dry_run": True,
            "note": "FORCE OVERRIDE",
        },
        headers=admin_headers,
    )
    assert proposal_force.status_code == 200
    proposal_force_id = proposal_force.json()["proposal_id"]
    assert proposal_force_id is not None

    lift_stock = client.post(
        "/stock-movements",
        json={
            "product_id": p_force_only.json()["id"],
            "movement_type": "IN",
            "quantity": 10,
            "note": "lift above reorder level",
        },
        headers=admin_headers,
    )
    assert lift_stock.status_code == 200

    with_force = client.post(
        f"/reorders/proposals/{proposal_force_id}/approve?force=true",
        headers=admin_headers,
    )
    assert with_force.status_code == 200
    forced_payload = with_force.json()
    assert len(forced_payload["applied"]) == 1
    assert len(forced_payload["blocked"]) == 0


def test_notifications_emission_and_read_flow(client):
    admin_headers = _auth_header(client, "admin", "admin123")
    clerk_headers = _auth_header(client, "clerk", "clerk123")

    wh = client.post(
        "/warehouses",
        json={"name": "Warehouse-N", "location": "Welkom"},
        headers=admin_headers,
    )
    assert wh.status_code == 200
    wh_id = wh.json()["id"]

    product = client.post(
        "/products",
        json={
            "sku": "SKU-T13-NOTIFY",
            "name": "Notify Product",
            "warehouse_id": wh_id,
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 3,
        },
        headers=admin_headers,
    )
    assert product.status_code == 200

    observed = client.get("/alerts/low-stock", headers=clerk_headers)
    assert observed.status_code == 200

    proposal = client.post(
        "/reorders/suggested",
        json={
            "warehouse_id": wh_id,
            "product_ids": [product.json()["id"]],
            "dry_run": True,
            "note": "NOTIFY PROPOSAL",
        },
        headers=admin_headers,
    )
    assert proposal.status_code == 200
    proposal_id = proposal.json()["proposal_id"]
    assert proposal_id is not None

    approved = client.post(
        f"/reorders/proposals/{proposal_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200

    notifications = client.get("/notifications?unread_only=true", headers=clerk_headers)
    assert notifications.status_code == 200
    rows = notifications.json()
    assert len(rows) >= 3
    event_types = {row["event_type"] for row in rows}
    assert "low_stock_observed" in event_types
    assert "reorder_proposal_submitted" in event_types
    assert "reorder_proposal_approved" in event_types

    first_id = rows[0]["id"]
    mark_read = client.post(f"/notifications/{first_id}/read", headers=clerk_headers)
    assert mark_read.status_code == 200
    assert mark_read.json()["is_read"] == 1

    unread_after = client.get("/notifications?unread_only=true", headers=clerk_headers)
    assert unread_after.status_code == 200
    assert all(n["id"] != first_id for n in unread_after.json())


def test_daily_reorder_scan_job_idempotency(client):
    admin_headers = _auth_header(client, "admin", "admin123")

    wh = client.post(
        "/warehouses",
        json={"name": "Warehouse-O", "location": "Rustenburg"},
        headers=admin_headers,
    )
    assert wh.status_code == 200
    wh_id = wh.json()["id"]

    product = client.post(
        "/products",
        json={
            "sku": "SKU-T14-JOB",
            "name": "Job Product",
            "warehouse_id": wh_id,
            "quantity_on_hand": 1,
            "reorder_level": 5,
            "reorder_quantity": 4,
        },
        headers=admin_headers,
    )
    assert product.status_code == 200

    first = client.post("/jobs/daily-reorder-scan", headers=admin_headers)
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["proposals_created"] >= 1
    assert len(first_payload["proposal_ids"]) >= 1

    second = client.post("/jobs/daily-reorder-scan", headers=admin_headers)
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["proposals_created"] == 0
    assert second_payload["skipped_existing_runs"] >= 1

    pending = client.get("/reorders/proposals?status=pending", headers=admin_headers)
    assert pending.status_code == 200
    assert any(p["id"] == first_payload["proposal_ids"][0] for p in pending.json())

    notifications = client.get(
        "/notifications?event_type=daily_reorder_scan_summary",
        headers=admin_headers,
    )
    assert notifications.status_code == 200
    assert len(notifications.json()) >= 2
