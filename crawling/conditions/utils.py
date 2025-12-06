from urllib.parse import urlparse
import re

def get_store_home_url(cur_url: str) -> str:
    try:
        p = urlparse(cur_url)
        parts = (p.path or "").strip("/").split("/")
        store_id = parts[0] if parts else ""
        if store_id and p.netloc in ("smartstore.naver.com", "brand.naver.com"):
            return f"{p.scheme}://{p.netloc}/{store_id}"
    except Exception:
        pass
    return cur_url

def _clean_store_title(title: str) -> str:
    t = (title or "").strip()

    # 앞에 붙는 "판매자정보 :" / "판매자 정보 :" 제거
    t = re.sub(r'^\s*판매자\s*정보\s*[:：]\s*', '', t)

    # (선택) 뒤에 붙는 흔한 꼬리 제거: " - 네이버 스마트스토어" 같은 형태
    t = re.sub(r'\s*[-|]\s*네이버.*$', '', t)

    return t.strip()

def get_store_name_fallback(driver) -> str:
    try:
        return _clean_store_title(driver.title)
    except Exception:
        return ""