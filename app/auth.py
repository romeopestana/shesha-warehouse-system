from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AppUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
password_context = CryptContext(schemes=["argon2"], deprecated="auto")


class User(BaseModel):
    username: str
    role: str
    disabled: bool = False


class UserInDB(User):
    hashed_password: str


def hash_password(plain_password: str) -> str:
    return password_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, username: str, password: str) -> UserInDB | None:
    user = db.query(AppUser).filter(AppUser.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return UserInDB(
        username=user.username,
        role=user.role,
        disabled=bool(user.disabled),
        hashed_password=user.hashed_password,
    )


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        username = payload.get("sub")
        role = payload.get("role")
        if username is None or role is None:
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc

    user = db.query(AppUser).filter(AppUser.username == username).first()
    if user is None or bool(user.disabled):
        raise credentials_error
    return User(username=user.username, role=user.role, disabled=bool(user.disabled))


def require_roles(*roles: str):
    def checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return checker
