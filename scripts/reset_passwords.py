import getpass

from sqlalchemy import select

from app import models  # noqa: F401
from app.auth import hash_password
from app.db import SessionLocal
from app.models import User

EMAILS = [
    "admin@trustvault.test",
    "owner1@trustvault.test",
    "owner2@trustvault.test",
    "viewer@trustvault.test",
]

password = getpass.getpass("New password for the demo users (min 12 characters): ")
if password != getpass.getpass("Type it again: "):
    raise SystemExit("The two entries do not match.")
if len(password) < 12:
    raise SystemExit("Password too short.")

with SessionLocal() as db:
    for email in EMAILS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print("not found:", email)
            continue
        user.password_hash = hash_password(password)
        user.token_version += 1  # any old login token stops working
        print("updated:", email)
    db.commit()