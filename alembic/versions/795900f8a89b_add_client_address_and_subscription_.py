"""Add client address and subscription fields

Revision ID: 795900f8a89b
Revises: 6bb16e7a818a
Create Date: 2026-07-27 09:30:14.874420

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '795900f8a89b'
down_revision: Union[str, None] = '6bb16e7a818a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём ENUM тип
    op.execute("CREATE TYPE clienttype AS ENUM ('LEGAL', 'INDIVIDUAL')")

    # Добавляем колонки
    op.add_column('clients', sa.Column('type', sa.Enum('LEGAL', 'INDIVIDUAL', name='clienttype'), nullable=False,
                                       server_default='LEGAL'))
    op.add_column('clients', sa.Column('kpp', sa.String(length=9), nullable=True))
    op.add_column('clients', sa.Column('subscription_end_date', sa.Date(), nullable=True))
    op.drop_column('clients', 'address')

    # Создаём таблицу client_addresses
    op.create_table('client_addresses',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('client_id', sa.Integer(), nullable=False),
                    sa.Column('address', sa.String(length=500), nullable=False),
                    sa.Column('fias_id', sa.String(length=36), nullable=True),
                    sa.Column('is_primary', sa.Boolean(), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
                    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_client_addresses_client_id'), 'client_addresses', ['client_id'], unique=False)
    op.create_index(op.f('ix_client_addresses_id'), 'client_addresses', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_client_addresses_id'), table_name='client_addresses')
    op.drop_index(op.f('ix_client_addresses_client_id'), table_name='client_addresses')
    op.drop_table('client_addresses')
    op.add_column('clients', sa.Column('address', sa.TEXT(), nullable=True))
    op.drop_column('clients', 'subscription_end_date')
    op.drop_column('clients', 'kpp')
    op.drop_column('clients', 'type')
    # Удаляем ENUM
    op.execute("DROP TYPE clienttype")