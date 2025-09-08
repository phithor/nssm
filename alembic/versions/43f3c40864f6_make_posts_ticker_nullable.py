"""make_posts_ticker_nullable

Revision ID: 43f3c40864f6
Revises: 2b5c38e617c8
Create Date: 2025-09-08 14:28:40.654752

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '43f3c40864f6'
down_revision = '2b5c38e617c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make ticker column nullable to allow general forum posts without specific tickers
    op.alter_column('posts', 'ticker', nullable=True)


def downgrade() -> None:
    # Revert ticker column to NOT NULL (note: may fail if NULL values exist)
    op.alter_column('posts', 'ticker', nullable=False)
