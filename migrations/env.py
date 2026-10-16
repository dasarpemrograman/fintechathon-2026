from alembic import context
from services.api.settings import settings
from services.api.store import engine
from migrations.schema_v1 import metadata

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
