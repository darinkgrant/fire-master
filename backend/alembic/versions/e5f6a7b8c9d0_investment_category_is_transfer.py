""""Investment" category -> transfer

Monarch files brokerage buys (a money-fund purchase, say) as "Investment" under
the Financial group, outside the Investments group f8a9b0c1d2e3 already flips,
so one large buy landed in the Runway's trailing burn as spending. Flip the
existing mapping; classify_flags() applies the same rule to future syncs.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from typing import Sequence, Union

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE category_mappings SET is_transfer = true, is_income = false "
        "WHERE normalized_category = 'Investment'"
    )


def downgrade() -> None:
    # Nothing to undo: putting the wrong spending flag back is not a rollback anyone wants.
    pass
