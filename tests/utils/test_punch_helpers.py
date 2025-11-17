from types import SimpleNamespace

from backend.app.utils import punch_helpers
from backend.app.models.punch_record import PunchType


def test_is_helpers_accept_enum_and_objects():
    punch = SimpleNamespace(punch_type=PunchType.IN)
    assert punch_helpers.is_in(punch)
    assert not punch_helpers.is_out(punch)

    assert punch_helpers.is_out(PunchType.OUT.value)
    assert punch_helpers.is_outside(SimpleNamespace(punch_type="outside"))
    assert punch_helpers.is_return(PunchType.RETURN)


def test_valid_transitions_match_status_map():
    assert punch_helpers.VALID_TRANSITIONS[PunchType.IN] == [PunchType.OUTSIDE, PunchType.OUT]
    assert punch_helpers.DISPLAY_NAMES[PunchType.OUTSIDE] == "外出"
    assert punch_helpers.STATUS_MAP[PunchType.OUT.value] == "退勤済"
