"""add_client_inventory_relation

Revision ID: 343422e678e4
Revises: f1b3fe3d9aab
Create Date: 2026-07-29 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql   # <-- добавить

# revision identifiers, used by Alembic.
revision: str = '343422e678e4'
down_revision: Union[str, None] = 'f1b3fe3d9aab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создать ENUM тип
    postgresql.ENUM('SANDBOX', 'PRODUCTION', name='czenvironment').create(op.get_bind(), checkfirst=True)
    
    op.add_column(
        'clients', 
        sa.Column(
            'cz_environment', 
            sa.Enum('SANDBOX', 'PRODUCTION', name='czenvironment'), 
            nullable=False,
            server_default='SANDBOX'   # <-- добавляем значение по умолчанию
        )
    )
    op.add_column('clients', sa.Column('cz_token', sa.String(length=500), nullable=True))
    op.add_column('clients', sa.Column('cz_api_url', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'cz_api_url')
    op.drop_column('clients', 'cz_token')
    op.drop_column('clients', 'cz_environment')
    
    # Удалить ENUM тип
    postgresql.ENUM(name='czenvironment').drop(op.get_bind(), checkfirst=True)