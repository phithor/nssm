"""merge migration branches

Revision ID: merge_branches_001
Revises: 3a9ac292e731, e4f8c9a7b2d1
Create Date: 2025-09-05 13:30:00.000000

"""

# revision identifiers, used by Alembic.
revision = "merge_branches_001"
down_revision = ("3a9ac292e731", "e4f8c9a7b2d1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration - no changes needed
    pass


def downgrade() -> None:
    # This is a merge migration - no changes needed
    pass
