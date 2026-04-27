from app.auth import hash_password
from app.database import SessionLocal
from app.models import AppUser


def seed_clerk(username: str = "clerk", password: str = "clerk123") -> None:
    db = SessionLocal()
    try:
        existing = db.query(AppUser).filter(AppUser.username == username).first()
        if existing:
            print(f"Clerk user '{username}' already exists.")
            return

        user = AppUser(
            username=username,
            hashed_password=hash_password(password),
            role="clerk",
            disabled=0,
        )
        db.add(user)
        db.commit()
        print(f"Clerk user '{username}' created.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_clerk()
