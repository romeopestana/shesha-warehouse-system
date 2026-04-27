from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])


@router.get("/admin/reorders", response_class=HTMLResponse)
def reorder_admin_ui():
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Shesha Reorder Admin</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f7f7f7; color: #222; }
    .card { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
    h1, h2, h3 { margin-top: 0; }
    label { display: block; margin: 8px 0 4px; font-size: 14px; }
    input, textarea, button { padding: 8px; border: 1px solid #bbb; border-radius: 6px; font-size: 14px; }
    input[type="checkbox"] { transform: scale(1.1); margin-right: 6px; }
    button { cursor: pointer; margin-right: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th, td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; font-size: 14px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; }
    .field { min-width: 220px; }
    .muted { color: #666; font-size: 13px; }
    .ok { color: #176f2c; }
    .err { color: #a01d1d; }
  </style>
</head>
<body>
  <h1>Reorder Proposal Admin</h1>
  <p class="muted">Manual approvals only. Set quantities per item, then approve.</p>

  <div class="card">
    <h2>Login</h2>
    <div class="row">
      <div class="field">
        <label for="username">Username</label>
        <input id="username" value="admin" />
      </div>
      <div class="field">
        <label for="password">Password</label>
        <input id="password" type="password" />
      </div>
    </div>
    <div style="margin-top: 12px;">
      <button onclick="login()">Login</button>
      <span id="authStatus" class="muted">Not logged in</span>
    </div>
  </div>

  <div class="card">
    <h2>Pending Proposals</h2>
    <button onclick="loadPending()">Refresh Pending</button>
    <span id="loadStatus" class="muted"></span>
    <div id="proposalList" style="margin-top: 12px;"></div>
  </div>

  <script>
    let accessToken = "";

    function setStatus(elId, text, cssClass) {
      const el = document.getElementById(elId);
      el.className = cssClass || "muted";
      el.textContent = text;
    }

    async function api(path, options = {}) {
      const headers = options.headers || {};
      if (accessToken) headers["Authorization"] = "Bearer " + accessToken;
      if (!headers["Content-Type"] && options.body) headers["Content-Type"] = "application/json";
      const resp = await fetch(path, { ...options, headers });
      const text = await resp.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { raw: text }; }
      if (!resp.ok) {
        throw new Error(data.detail || JSON.stringify(data));
      }
      return data;
    }

    async function login() {
      const username = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value;
      const body = new URLSearchParams({ username, password });
      try {
        const resp = await fetch("/auth/token", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: body.toString()
        });
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Login failed");
        }
        accessToken = data.access_token;
        setStatus("authStatus", "Logged in as " + username, "ok");
        await loadPending();
      } catch (err) {
        setStatus("authStatus", "Login failed: " + err.message, "err");
      }
    }

    function proposalHtml(p) {
      const rows = p.items.map((item) => {
        return `
          <tr>
            <td>${item.id}</td>
            <td>${item.product_id}</td>
            <td>${item.warehouse_id}</td>
            <td>${item.quantity_before}</td>
            <td>${item.quantity_added}</td>
            <td><input type="number" min="1" id="q-${p.id}-${item.id}" value="${item.quantity_added}" /></td>
          </tr>
        `;
      }).join("");

      return `
        <div class="card">
          <h3>Proposal #${p.id}</h3>
          <div class="muted">Note: ${p.note || "(none)"} | Created by: ${p.created_by}</div>
          <table>
            <thead>
              <tr>
                <th>Item ID</th>
                <th>Product ID</th>
                <th>Warehouse ID</th>
                <th>Qty Before</th>
                <th>Suggested Qty</th>
                <th>Approve Qty</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
          <div style="margin-top: 10px;">
            <label><input type="checkbox" id="force-${p.id}" /> Use force=true (stock-level drift only)</label>
            <button onclick="approveProposal(${p.id}, ${encodeURIComponent(JSON.stringify(p.items))})">Approve</button>
            <button onclick="rejectProposal(${p.id})">Reject</button>
            <span id="status-${p.id}" class="muted"></span>
          </div>
        </div>
      `;
    }

    async function loadPending() {
      if (!accessToken) {
        setStatus("loadStatus", "Please log in first.", "err");
        return;
      }
      try {
        const proposals = await api("/reorders/proposals?status=pending");
        const container = document.getElementById("proposalList");
        if (!proposals.length) {
          container.innerHTML = '<div class="muted">No pending proposals.</div>';
        } else {
          container.innerHTML = proposals.map(proposalHtml).join("");
        }
        setStatus("loadStatus", "Loaded " + proposals.length + " pending proposal(s).", "ok");
      } catch (err) {
        setStatus("loadStatus", "Load failed: " + err.message, "err");
      }
    }

    async function approveProposal(proposalId, encodedItemsJson) {
      const items = JSON.parse(decodeURIComponent(encodedItemsJson));
      const item_quantities = [];
      for (const item of items) {
        const input = document.getElementById(`q-${proposalId}-${item.id}`);
        const qty = Number(input.value);
        if (!Number.isInteger(qty) || qty <= 0) {
          setStatus(`status-${proposalId}`, `Invalid quantity for item ${item.id}.`, "err");
          return;
        }
        item_quantities.push({ item_id: item.id, quantity_added: qty });
      }
      const force = document.getElementById(`force-${proposalId}`).checked;
      const path = force
        ? `/reorders/proposals/${proposalId}/approve?force=true`
        : `/reorders/proposals/${proposalId}/approve`;
      try {
        const payload = await api(path, { method: "POST", body: JSON.stringify({ item_quantities }) });
        const blocked = payload.blocked ? payload.blocked.length : 0;
        setStatus(`status-${proposalId}`, `Approved. Applied: ${payload.applied.length}, blocked: ${blocked}`, "ok");
        await loadPending();
      } catch (err) {
        setStatus(`status-${proposalId}`, "Approve failed: " + err.message, "err");
      }
    }

    async function rejectProposal(proposalId) {
      const reason = prompt("Rejection reason:");
      if (!reason) return;
      try {
        await api(`/reorders/proposals/${proposalId}/reject`, {
          method: "POST",
          body: JSON.stringify({ reason })
        });
        setStatus(`status-${proposalId}`, "Rejected.", "ok");
        await loadPending();
      } catch (err) {
        setStatus(`status-${proposalId}`, "Reject failed: " + err.message, "err");
      }
    }
  </script>
</body>
</html>
"""
