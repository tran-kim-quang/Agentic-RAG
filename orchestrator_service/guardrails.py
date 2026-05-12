"""Basic guardrails for sales responses."""
import re

FORBIDDEN_PATTERNS = [
    re.compile(r"\b(giá\s+chính\s+xác\s+là)\b", re.I),
    re.compile(r"\b(chắc\s+chắn\s+100%)\b", re.I),
    re.compile(r"\b(lừa\s+đảo|lừa\s+gạt)\b", re.I),
]


def check_hallucination(answer: str, chunks: list) -> tuple[bool, str]:
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(answer):
            return False, "Phát hiện từ ngữ không phù hợp trong phản hồi."
    return True, ""


def sanitize_response(answer: str) -> str:
    # Trim excessive length
    if len(answer) > 2000:
        answer = answer[:2000] + "\n\n[Dạ em xin phép trả lời ngắn gọn thôi ạ.]"
    return answer
