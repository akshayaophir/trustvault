import getpass

from sqlalchemy import select

from app import models  # noqa: F401
from app.auth import hash_password
from app.db import SessionLocal
from app.models import User

USERS = [
    ("admin@trustvault.test", "admin"),
    ("owner1@trustvault.test", "owner"),
    ("owner2@trustvault.test", "owner"),
    ("viewer@trustvault.test", "viewer"),
]

password = getpass.getpass("Password for the seed users (min 12 characters): ")
if len(password) < 12:
    raise SystemExit("Password too short.")

with SessionLocal() as db:
    for email, role in USERS:
        if db.scalar(select(User).where(User.email == email)):
            print("already exists:", email)
            continue
        db.add(User(email=email, password_hash=hash_password(password), role=role))
        print("created:", email, role)
    db.commit()