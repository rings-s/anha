"""add bilingual service descriptions

Revision ID: b3c4d5e6f7a8
Revises: 90372c868171
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = '90372c868171'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('services', sa.Column('description_ar', sa.Text(), nullable=True))
    op.add_column('services', sa.Column('description_en', sa.Text(), nullable=True))
    # Migrate existing description data to description_ar (assumed Arabic)
    op.execute("UPDATE services SET description_ar = description WHERE description IS NOT NULL")


def downgrade() -> None:
    op.drop_column('services', 'description_en')
    op.drop_column('services', 'description_ar')
