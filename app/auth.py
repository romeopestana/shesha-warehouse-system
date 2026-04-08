from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class User(BaseModel):
    username: str
    role: str
    disabled: bool = False


class UserInDB(User):
    password: str


# Demo users for initial scaffold.
fake_users_db = {
    "admin": UserInDB(
        username="admin",
        role="admin",
        disabled=False,
        password="admin123",
    ),
    "clerk": UserInDB(
        username="clerk",
        role="clerk",
        disabled=False,
        password="clerk123",
    ),
}


def verify_password(plain_password: str, saved_password: str) -> bool:
    return plain_password == saved_password


def authenticate_user(username: str, password: str) -> UserInDB | None:
    user = fake_users_db.get(username)
    if not user or not verify_password(password, user.password):
        return None
    return user


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
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

    user = fake_users_db.get(username)
    if user is None or user.disabled:
        raise credentials_error
    return User(username=user.username, role=user.role, disabled=user.disabled)


def require_roles(*roles: str):
    def checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return checker
