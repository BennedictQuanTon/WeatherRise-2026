"""Deterministic response-language detection."""

from __future__ import annotations

import re
from typing import Literal


ResponseLanguage = Literal["en", "vi"]

_VIETNAMESE_DIACRITICS = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễ"
    r"ìíịỉĩòóọỏõôồốộổỗơờớợởỡ"
    r"ùúụủũưừứựửữỳýỵỷỹđ"
    r"ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄ"
    r"ÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ"
    r"ÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
)

_VIETNAMESE_TERMS = {
    "thoi tiet",
    "thời tiết",
    "tuan sau",
    "tuần sau",
    "ngay mai",
    "ngày mai",
    "cuoi tuan",
    "cuối tuần",
    "co nen",
    "có nên",
    "du lich",
    "du lịch",
    "lich trinh",
    "lịch trình",
    "di choi",
    "đi chơi",
    "di du lich",
    "đi du lịch",
    "mua",
    "mưa",
    "nắng",
    "gio",
    "gió",
    "nhiet do",
    "nhiệt độ",
    "hai san",
    "hải sản",
    "ăn",
    "xay dung",
    "xây dựng",
    "nong trai",
    "nông trại",
    "trang trai",
    "trang trại",
}


def detect_response_language(raw_user_input: str | None) -> ResponseLanguage:
    """Return `vi` only when the user input is clearly Vietnamese."""
    text = (raw_user_input or "").strip()
    if not text:
        return "en"

    if _VIETNAMESE_DIACRITICS.search(text):
        return "vi"

    normalized = text.lower()
    matches = sum(1 for term in _VIETNAMESE_TERMS if term in normalized)
    if matches >= 2:
        return "vi"
    return "en"
