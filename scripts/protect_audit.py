from app.audit_protect import install_audit_triggers
from app.db import engine

install_audit_triggers(engine)
print("audit_log is now append-only: updates and deletes are blocked")