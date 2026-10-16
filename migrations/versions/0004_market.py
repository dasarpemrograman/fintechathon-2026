"""Market observations preserve original price and applicability dimensions."""

from alembic import op
from migrations.schema_v4 import market_observations

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    market_observations.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError(
        "Preserve source history with a forward migration or verified backup."
    )
