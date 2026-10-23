STATEMENTS = [
    """CREATE OR REPLACE FUNCTION audit_log_block_change() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log",
    """CREATE TRIGGER audit_log_no_update_delete
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION audit_log_block_change()""",
]


def install_audit_triggers(engine):
    with engine.begin() as conn:
        for sql in STATEMENTS:
            conn.exec_driver_sql(sql)