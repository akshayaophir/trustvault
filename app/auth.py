from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

ph = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
TOKEN_HOURS = 8
DUMMY_HASH = ph.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "tv": user.token_version,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def unauthorized():
    return HTTPException(status_code=401, detail="Not authenticated")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise unauthorized()
    try:
        data = jwt.decode(creds.credentials, settings.secret_key, algorithms=["HS256"])
        user_id = int(data["sub"])
        token_version = data["tv"]
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized()

    # The user and role always come from the database, never from the token.
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != token_version:
        raise unauthorized()
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return checker