"""
아이디/닉네임에 쓸 수 없는 단어(금칙어) 검사.

지금은 아주 짧은 예시 목록으로 시작합니다.
8단계(금칙어 시스템)에서 이 목록을 DB로 옮기고, 관리자페이지에서
등록/수정/삭제할 수 있도록 확장할 예정입니다. 지금은 최소한의
욕설/비속어만 걸러내는 용도입니다.
"""

# TODO(8단계): DB 기반 금칙어 관리로 교체
BANNED_WORDS = [
    "씨발", "시발", "병신", "좆", "fuck", "shit",
]


def contains_banned_word(text: str) -> bool:
    """text 안에 금칙어가 포함되어 있으면 True를 반환합니다."""
    lowered = text.lower()
    return any(word in lowered for word in BANNED_WORDS)
