from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.auth import User, authenticate_user
from app.config import settings
from app.database import get_db
from app.models import AppUser, ReorderProposal
from app.routers.reorder import approve_reorder_proposal, reject_reorder_proposal
from app.schemas import ReorderProposalApproveRequest, ReorderProposalRejectRequest

router = APIRouter(tags=["ui"])
SESSION_COOKIE_NAME = "admin_session"


def _user_from_session_cookie(
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    db: Session = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            session_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        username = payload.get("sub")
        role = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc
    user = db.query(AppUser).filter(AppUser.username == username).first()
    if user is None or bool(user.disabled):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return User(username=user.username, role=user.role, disabled=bool(user.disabled))


def _require_admin_ui(user: User = Depends(_user_from_session_cookie)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


@router.post("/admin/session/login")
def admin_ui_login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    token = jwt.encode(
        {"sub": user.username, "role": user.role},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return {"username": user.username, "role": user.role}


@router.post("/admin/session/logout")
def admin_ui_logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/admin/session/me")
def admin_ui_me(current_user: User = Depends(_require_admin_ui)):
    return {"username": current_user.username, "role": current_user.role}


@router.get("/admin/api/reorders/proposals")
def admin_ui_list_proposals(
    status: str | None = Query(default="pending"),
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin_ui),
):
    query = db.query(ReorderProposal)
    if status is not None:
        query = query.filter(ReorderProposal.status == status)
    return query.order_by(ReorderProposal.id.desc()).all()


@router.post("/admin/api/reorders/proposals/{proposal_id}/approve")
def admin_ui_approve(
    proposal_id: int,
    payload: ReorderProposalApproveRequest,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin_ui),
):
    return approve_reorder_proposal(
        proposal_id=proposal_id,
        payload=payload,
        db=db,
        current_user=current_user,
        force=force,
    )


@router.post("/admin/api/reorders/proposals/{proposal_id}/reject")
def admin_ui_reject(
    proposal_id: int,
    payload: ReorderProposalRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin_ui),
):
    return reject_reorder_proposal(
        proposal_id=proposal_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )


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

  <div class="card">
    <h2>API Response Windows</h2>
    <p class="muted">Live payloads from UI API calls for easier troubleshooting and auditing.</p>
    <div class="row">
      <div class="field" style="flex: 1 1 420px;">
        <label>GET /admin/session/me</label>
        <pre id="api-session-me" style="min-height: 120px; background: #111; color: #f1f1f1; padding: 10px; border-radius: 6px; overflow:auto;">(no response yet)</pre>
      </div>
      <div class="field" style="flex: 1 1 420px;">
        <label>GET /admin/api/reorders/proposals?status=pending</label>
        <pre id="api-proposals" style="min-height: 120px; background: #111; color: #f1f1f1; padding: 10px; border-radius: 6px; overflow:auto;">(no response yet)</pre>
      </div>
      <div class="field" style="flex: 1 1 420px;">
        <label>POST /admin/api/reorders/proposals/{id}/approve</label>
        <pre id="api-approve" style="min-height: 120px; background: #111; color: #f1f1f1; padding: 10px; border-radius: 6px; overflow:auto;">(no response yet)</pre>
      </div>
      <div class="field" style="flex: 1 1 420px;">
        <label>POST /admin/api/reorders/proposals/{id}/reject</label>
        <pre id="api-reject" style="min-height: 120px; background: #111; color: #f1f1f1; padding: 10px; border-radius: 6px; overflow:auto;">(no response yet)</pre>
      </div>
    </div>
  </div>

  <script>
    function setApiWindow(elId, payload) {
      const el = document.getElementById(elId);
      el.textContent = JSON.stringify(payload, null, 2);
    }

    function setStatus(elId, text, cssClass) {
      const el = document.getElementById(elId);
      el.className = cssClass || "muted";
      el.textContent = text;
    }

    async function api(path, options = {}) {
      const headers = options.headers || {};
      if (!headers["Content-Type"] && options.body) headers["Content-Type"] = "application/json";
      const resp = await fetch(path, { ...options, headers, credentials: "include" });
      const text = await resp.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) { data = { raw: text }; }
      const apiWindowId = options.apiWindowId || null;
      if (apiWindowId) {
        setApiWindow(apiWindowId, { path, status: resp.status, payload: data });
      }
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
        const resp = await fetch("/admin/session/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: body.toString(),
          credentials: "include"
        });
        const data = await resp.json();
        if (!resp.ok) {
          throw new Error(data.detail || "Login failed");
        }
        setApiWindow("api-session-me", { login: data });
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
      try {
        const proposals = await api("/admin/api/reorders/proposals?status=pending", { apiWindowId: "api-proposals" });
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
        ? `/admin/api/reorders/proposals/${proposalId}/approve?force=true`
        : `/admin/api/reorders/proposals/${proposalId}/approve`;
      const summary = item_quantities.map((x) => `item ${x.item_id}: ${x.quantity_added}`).join(", ");
      if (!confirm(`Approve proposal #${proposalId} with quantities: ${summary}?`)) return;
      try {
        const payload = await api(path, {
          method: "POST",
          body: JSON.stringify({ item_quantities }),
          apiWindowId: "api-approve",
        });
        const blocked = payload.blocked ? payload.blocked.length : 0;
        const blockedReasons = (payload.blocked || []).map((b) => `item ${b.item_id}: ${b.reason}`).join("; ");
        const suffix = blockedReasons ? ` | ${blockedReasons}` : "";
        setStatus(`status-${proposalId}`, `Approved. Applied: ${payload.applied.length}, blocked: ${blocked}${suffix}`, "ok");
        await loadPending();
      } catch (err) {
        setApiWindow("api-approve", { error: err.message, proposalId, force, item_quantities });
        setStatus(`status-${proposalId}`, "Approve failed: " + err.message, "err");
      }
    }

    async function rejectProposal(proposalId) {
      const reason = prompt("Rejection reason:");
      if (!reason) return;
      try {
        const payload = await api(`/admin/api/reorders/proposals/${proposalId}/reject`, {
          method: "POST",
          body: JSON.stringify({ reason }),
          apiWindowId: "api-reject",
        });
        setStatus(`status-${proposalId}`, "Rejected.", "ok");
        await loadPending();
      } catch (err) {
        setApiWindow("api-reject", { error: err.message, proposalId, reason });
        setStatus(`status-${proposalId}`, "Reject failed: " + err.message, "err");
      }
    }

    window.addEventListener("load", async () => {
      try {
        const who = await api("/admin/session/me", { apiWindowId: "api-session-me" });
        setStatus("authStatus", "Active session as " + who.username, "ok");
        await loadPending();
      } catch (_) {
        setStatus("authStatus", "Not logged in", "muted");
      }
    });
  </script>
</body>
</html>
"""
