"""Sales discovery workflow helpers."""
from typing import Dict, Any


DISCOVERY_QUESTIONS = {
    "budget": "Anh/chị đang có ngân sách khoảng bao nhiêu ạ?",
    "purpose": "Anh/chị mua để ở hay đầu tư cho thuê ạ?",
    "area": "Anh/chị quan tâm khu vực nào ạ?",
    "bedrooms": "Anh/chị cần mấy phòng ngủ ạ?",
    "timeline": "Anh/chị dự kiến mua trong khoảng thời gian nào ạ?",
}


def next_discovery_question(profile: Dict[str, Any]) -> str:
    for key, question in DISCOVERY_QUESTIONS.items():
        if key not in profile or not profile[key]:
            return question
    return "Anh/chị cần em tư vấn thêm điều gì không ạ?"


def update_profile_from_intent(profile: Dict[str, Any], intent: str, text: str) -> Dict[str, Any]:
    # Naive keyword extraction; can be replaced with structured extraction
    if "tỷ" in text or "triệu" in text or "ngân sách" in text:
        profile["budget"] = text
    if "ở" in text or "thuê" in text:
        profile["purpose"] = text
    if "phòng ngủ" in text or "PN" in text:
        profile["bedrooms"] = text
    if "quận" in text or "huyện" in text or "khu vực" in text:
        profile["area"] = text
    profile["last_intent"] = intent
    return profile
