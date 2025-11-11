"""
PunchType遷移の単体テスト
"""

from enum import Enum

try:
    from backend.app.models.punch_record import PunchType  # type: ignore
except Exception:
    class PunchType(str, Enum):
        IN = "in"
        OUT = "out"
        OUTSIDE = "outside"
        RETURN = "return"

from backend.app.utils.punch_helpers import VALID_TRANSITIONS


def test_valid_transitions():
    assert PunchType.OUT in VALID_TRANSITIONS[PunchType.IN]
    assert PunchType.RETURN in VALID_TRANSITIONS[PunchType.OUTSIDE]
    assert PunchType.OUT in VALID_TRANSITIONS[PunchType.RETURN]
    assert VALID_TRANSITIONS[PunchType.OUT] == []


def test_invalid_paths():
    assert PunchType.RETURN not in VALID_TRANSITIONS[PunchType.IN]
    assert PunchType.IN not in VALID_TRANSITIONS[PunchType.OUTSIDE]
