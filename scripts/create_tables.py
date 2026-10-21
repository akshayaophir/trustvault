from sqlalchemy import inspect

from app import models  # noqa: F401  (loads the table definitions)
from app.db import Base, engine

Base.metadata.create_all(engine)
print("Tables:", inspect(engine).get_table_names())