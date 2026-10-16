"""Isolated extraction cache prevents repeated document-page charges."""
from alembic import op
from migrations.schema_v6 import extractions
revision='0006';down_revision='0005';branch_labels=None;depends_on=None
def upgrade():extractions.create(op.get_bind(),checkfirst=True)
def downgrade():raise RuntimeError('Preserve extraction provenance with forward migrations.')
