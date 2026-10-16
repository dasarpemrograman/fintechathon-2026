"""Encrypted connector credentials, OAuth state and event ownership."""

from alembic import op
from migrations.schema_v3 import connector_credentials, oauth_states, calendar_events

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    for table in [connector_credentials, oauth_states, calendar_events]:
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError(
        "Connector history requires export and retention review; use a forward migration."
    )
