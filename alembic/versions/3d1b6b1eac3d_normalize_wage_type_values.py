"""Normalize wage_type values to uppercase

Revision ID: 3d1b6b1eac3d
Revises: e6563347355d
Create Date: 2025-11-11 09:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3d1b6b1eac3d"
down_revision: Union[str, None] = "e6563347355d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE employees SET wage_type = 'HOURLY' WHERE wage_type IN ('hourly', 'Hourly', 'HOURLY')"
    )
    op.execute(
        "UPDATE employees SET wage_type = 'MONTHLY' WHERE wage_type IN ('monthly', 'Monthly', 'MONTHLY')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE employees SET wage_type = 'hourly' WHERE wage_type = 'HOURLY'"
    )
    op.execute(
        "UPDATE employees SET wage_type = 'monthly' WHERE wage_type = 'MONTHLY'"
    )
