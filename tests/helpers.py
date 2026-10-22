from app.auth import hash_password
from app.models import Document, Grant, User, now

_HASH = hash_password("test-password-123")


def make_user(db, email, role="viewer", active=True):
    user = User(email=email, password_hash=_HASH, role=role, is_active=active)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_doc(db, owner, name="secret.pdf"):
    doc = Document(owner_id=owner.id, name=name, mime="application/pdf", size=1, sha256="0" * 64)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def make_grant(db, doc, user, permission, granted_by, revoked=False):
    grant = Grant(
        document_id=doc.id, user_id=user.id, permission=permission, granted_by=granted_by.id
    )
    if revoked:
        grant.revoked_at = now()
    db.add(grant)
    db.commit()
    return grant