"""Income sources: optional take-home amount

net_annual_amount (cents/yr, nullable) is what reaches the bank after tax,
withholding and paycheck deductions. Cash-flow engines use it when set; the tax
engine keeps using the gross annual_amount. NULL keeps today's behavior.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("income_sources", sa.Column("net_annual_amount", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("income_sources", "net_annual_amount")
