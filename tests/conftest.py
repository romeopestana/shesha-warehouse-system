import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import AppUser

TEST_DB_PATH = "./test_app.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="session")
def test_engine():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(scope="function")
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        # Reset data between tests.
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()

        admin = AppUser(
            username="admin",
            hashed_password=hash_password("admin123"),
            role="admin",
            disabled=0,
        )
        clerk = AppUser(
            username="clerk",
            hashed_password=hash_password("clerk123"),
            role="clerk",
            disabled=0,
        )
        session.add_all([admin, clerk])
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
