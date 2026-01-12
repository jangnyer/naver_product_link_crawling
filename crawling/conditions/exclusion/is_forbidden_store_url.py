from urllib.parse import urlparse


def extract_store_key_from_url(url: str) -> str:
    """
    스마트스토어 URL에서 .com/ 뒤의 고유주소를 추출.
    예: https://smartstore.naver.com/innovad -> innovad
    """
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").strip("/")
        # 첫 번째 경로 조각을 추출 (예: innovad)
        first = path.split("/", 1)[0] if path else ""
        return first
    except Exception:
        return ""


def is_forbidden_store_url(url: str, forbidden_store_urls: set) -> bool:
    """
    스토어 URL이 금칙어 목록에 있는지 확인.
    url에서 .com/ 뒤의 고유주소만 추출하여 비교.
    """
    if not forbidden_store_urls:
        return False
    
    store_key = extract_store_key_from_url(url)
    if not store_key:
        return False
    
    # 금칙어 목록에 있는지 확인 (대소문자 무시)
    store_key_lower = store_key.lower()
    for forbidden in forbidden_store_urls:
        if forbidden.lower() == store_key_lower:
            return True
    
    return False

