import os

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

# This must run BEFORE the app is imported, so tests use the test database.
_env = dotenv_values(".env")
_main_url = os.environ.get("DATABASE_URL") or _env.get("DATABASE_URL")
_test_url = make_url(_main_url).set(database="trustvault_test")
os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)
os.environ["SECRET_KEY"] = "test-only-secret-key-not-used-anywhere-else"

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402,F401
from app.db import Base, SessionLocal, engine  # noqa: E402

# Safety net: refuse to run against anything that isn't the test database.
assert engine.url.database == "trustvault_test", "Refusing to run: not the test database"


@pytest.fixture(scope="session", autouse=True)
def create_schema():
    Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def clean_db():
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE audit_log, grants, documents, users RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session
