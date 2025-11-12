"""
打刻に関する共通ヘルパー

列挙値や状態遷移を一元管理し、将来的な変更に備える。
"""

from enum import Enum
from typing import Any, Dict, List

try:
    # プロジェクトで定義済みのPunchTypeを再利用
    from backend.app.models.punch_record import PunchType  # type: ignore
except Exception:
    # 型チェック・ドキュメント生成用のフォールバック定義
    class PunchType(str, Enum):
        IN = "in"
        OUT = "out"
        OUTSIDE = "outside"
        RETURN = "return"


VALID_TRANSITIONS: Dict[PunchType, List[PunchType]] = {
    PunchType.IN: [PunchType.OUTSIDE, PunchType.OUT],
    PunchType.OUTSIDE: [PunchType.RETURN],
    PunchType.RETURN: [PunchType.OUTSIDE, PunchType.OUT],
    PunchType.OUT: [],
}

DISPLAY_NAMES: Dict[PunchType, str] = {
    PunchType.IN: "出勤",
    PunchType.OUT: "退勤",
    PunchType.OUTSIDE: "外出",
    PunchType.RETURN: "戻り",
}

STATUS_MAP: Dict[str, str] = {
    PunchType.IN.value: "勤務中",
    PunchType.OUTSIDE.value: "外出中",
    PunchType.RETURN.value: "勤務中",
    PunchType.OUT.value: "退勤済",
}


def _field_value(punch: Any) -> Any:
    """Enum/文字列の両方を扱えるようにする"""
    value = getattr(punch, "punch_type", punch)
    return value.value if isinstance(value, Enum) else value


def is_in(punch: Any) -> bool:
    return _field_value(punch) == PunchType.IN.value


def is_out(punch: Any) -> bool:
    return _field_value(punch) == PunchType.OUT.value


def is_outside(punch: Any) -> bool:
    return _field_value(punch) == PunchType.OUTSIDE.value


def is_return(punch: Any) -> bool:
    return _field_value(punch) == PunchType.RETURN.value
