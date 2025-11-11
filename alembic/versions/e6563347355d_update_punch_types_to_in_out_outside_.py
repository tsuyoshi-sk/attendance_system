"""Update punch types to IN/OUT/OUTSIDE/RETURN

Revision ID: e6563347355d
Revises: e3f09acd99c7
Create Date: 2025-05-25 14:09:45.684868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6563347355d'
down_revision: Union[str, None] = 'e3f09acd99c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_TO_NEW = {
    "clock_in": "in",
    "CLOCK_IN": "in",
    "clock_out": "out",
    "CLOCK_OUT": "out",
    "break_start": "outside",
    "BREAK_START": "outside",
    "break_end": "return",
    "BREAK_END": "return",
}

NEW_TO_OLD = {
    "in": "clock_in",
    "out": "clock_out",
    "outside": "break_start",
    "return": "break_end",
}


def upgrade() -> None:
    for old_value, new_value in OLD_TO_NEW.items():
        op.execute(
            sa.text(
                "UPDATE punch_records SET punch_type = :new WHERE punch_type = :old"
            ).bindparams(new=new_value, old=old_value)
        )


def downgrade() -> None:
    for new_value, old_value in NEW_TO_OLD.items():
        op.execute(
            sa.text(
                "UPDATE punch_records SET punch_type = :old WHERE punch_type = :new"
            ).bindparams(old=old_value, new=new_value)
        )
