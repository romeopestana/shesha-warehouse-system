from app.auth import hash_password
from app.database import SessionLocal
from app.models import AppUser


def seed_admin(username: str = "admin", password: str = "admin123") -> None:
    db = SessionLocal()
    try:
        existing = db.query(AppUser).filter(AppUser.username == username).first()
        if existing:
            print(f"Admin user '{username}' already exists.")
            return

        user = AppUser(
            username=username,
            hashed_password=hash_password(password),
            role="admin",
            disabled=0,
        )
        db.add(user)
        db.commit()
        print(f"Admin user '{username}' created.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
