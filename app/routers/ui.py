from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import User, hash_password, require_roles, verify_password
from app.database import get_db
from app.models import AppUser

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["ui"])


@router.get("/", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")


class ChangeAdminPasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)


class CreateClerkRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


class ResetClerkPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6)


@router.get("/admin/users/clerks")
def list_clerks(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    clerks = db.query(AppUser).filter(AppUser.role == "clerk").order_by(AppUser.username.asc()).all()
    return [{"username": c.username, "disabled": int(c.disabled)} for c in clerks]


@router.post("/admin/users/clerks")
def create_clerk(
    payload: CreateClerkRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    existing = db.query(AppUser).filter(AppUser.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    clerk = AppUser(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="clerk",
        disabled=0,
    )
    db.add(clerk)
    db.commit()
    return {"ok": True, "username": clerk.username}


@router.post("/admin/users/clerks/{username}/block")
def block_clerk(
    username: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    clerk = db.query(AppUser).filter(AppUser.username == username, AppUser.role == "clerk").first()
    if not clerk:
        raise HTTPException(status_code=404, detail="Clerk not found")
    clerk.disabled = 1
    db.add(clerk)
    db.commit()
    return {"ok": True, "username": clerk.username, "disabled": int(clerk.disabled)}


@router.delete("/admin/users/clerks/{username}")
def remove_clerk(
    username: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    clerk = db.query(AppUser).filter(AppUser.username == username, AppUser.role == "clerk").first()
    if not clerk:
        raise HTTPException(status_code=404, detail="Clerk not found")
    db.delete(clerk)
    db.commit()
    return {"ok": True, "username": username}


@router.post("/admin/users/clerks/{username}/reset-password")
def reset_clerk_password(
    username: str,
    payload: ResetClerkPasswordRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    clerk = db.query(AppUser).filter(AppUser.username == username, AppUser.role == "clerk").first()
    if not clerk:
        raise HTTPException(status_code=404, detail="Clerk not found")
    clerk.hashed_password = hash_password(payload.new_password)
    clerk.disabled = 0
    db.add(clerk)
    db.commit()
    return {"ok": True, "username": clerk.username}


@router.post("/admin/users/admin/change-password")
def change_admin_password(
    payload: ChangeAdminPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    admin = db.query(AppUser).filter(AppUser.username == current_user.username).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin user not found")
    if not verify_password(payload.current_password, admin.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    admin.hashed_password = hash_password(payload.new_password)
    db.add(admin)
    db.commit()
    return {"ok": True, "username": admin.username}
