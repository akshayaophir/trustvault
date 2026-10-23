from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import DUMMY_HASH, create_token, get_current_user, verify_password
from app.db import get_db
from app.models import User
from app.routes import documents, grants

app = FastAPI(title="TrustVault")
app.include_router(documents.router)
app.include_router(grants.router)


class LoginIn(BaseModel):
    email: str
    password: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    # Always run one password check, so timing doesn't reveal whether the email exists.
    password_hash = user.password_hash if user else DUMMY_HASH
    ok = verify_password(password_hash, body.password)
    if not (user and ok and user.is_active):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(user), "token_type": "bearer"}


@app.post("/auth/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1  # invalidates every token issued to this user
    db.commit()
    return {"status": "logged out"}


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}