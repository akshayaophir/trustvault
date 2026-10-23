from sqlalchemy import text

from app.db import engine

with engine.begin() as conn:
    conn.execute(text("TRUNCATE audit_log"))
print("audit_log cleared (development rows from before the hash chain)")