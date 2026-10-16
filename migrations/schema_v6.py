"""Tenant and execution-scope isolated extraction cache."""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
metadata=sa.MetaData()
extractions=sa.Table('document_extractions',metadata,sa.Column('tenant_id',sa.Text,primary_key=True),sa.Column('content_hash',sa.Text,primary_key=True),sa.Column('parser_version',sa.Text,primary_key=True),sa.Column('scope',sa.Text,primary_key=True),sa.Column('pages',JSONB,nullable=False),sa.Column('page_count',sa.Integer,nullable=False),sa.Column('result_hash',sa.Text,nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
