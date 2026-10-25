import hashlib
from datetime import timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.routes import access_requests, admin, documents, grants
from app import audit
from app.auth import DUMMY_HASH, create_token, get_current_user, verify_password
from app.db import get_db
from app.models import AuditLog, User, now

STATIC = Path(__file__).parent / "static"
LOCK_AFTER = 5                   # failed logins before the account is locked
LOCK_WINDOW = timedelta(minutes=15)
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")

app = FastAPI(title="TrustVault")
app.include_router(documents.router)
app.include_router(grants.router)
app.include_router(admin.router)
app.include_router(access_requests.router)
if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    h = response.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "no-referrer")
    h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if not request.url.path.startswith("/static"):
        h.setdefault("Cache-Control", "no-store")
    if request.url.path == "/":
        h.setdefault("Content-Security-Policy", CSP)
    return response


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


@app.get("/", include_in_schema=False)
def home():
    index = STATIC / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"service": "TrustVault", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


def failed_logins(db: Session, key: str) -> int:
    """Failed logins for this email since the last successful one (max 15 minutes back)."""
    since = now() - LOCK_WINDOW
    last_ok = db.scalar(
        select(func.max(AuditLog.ts)).where(
            AuditLog.action == "login", AuditLog.outcome == "allowed",
            AuditLog.detail["h"].as_string() == key)
    )
    if last_ok and last_ok > since:
        since = last_ok
    return db.scalar(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "login", AuditLog.outcome == "denied",
            AuditLog.ts > since, AuditLog.detail["h"].as_string() == key)
    ) or 0


@app.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    key = hashlib.sha256(email.encode()).hexdigest()[:16]  # same for real and unknown emails

    if failed_logins(db, key) >= LOCK_AFTER:
        audit.log(db, None, "login_locked", "denied", detail={"h": key})
        db.commit()
        raise HTTPException(status_code=429,
                            detail="Too many failed attempts. Try again in 15 minutes.")

    user = db.scalar(select(User).where(User.email == email))
    # Always run one password check, so timing doesn't reveal whether the email exists.
    ok = verify_password(user.password_hash if user else DUMMY_HASH, body.password)
    if not (user and ok and user.is_active):
        audit.log(db, user, "login", "denied", detail={"h": key})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    audit.log(db, user, "login", "allowed", detail={"h": key})
    db.commit()
    return {"access_token": create_token(user), "token_type": "bearer"}


@app.post("/auth/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1  # invalidates every token issued to this user
    db.commit()
    return {"status": "logged out"}


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}