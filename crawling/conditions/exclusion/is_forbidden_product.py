def is_forbidden_name(name: str,FORBIDDEN_KEYWORDS) -> bool:
    """
    상품명에 금지어가 하나라도 포함되어 있으면 True.
    (부분 문자열 기준, 대소문자 구분 없음 – 한글은 그대로 비교)
    """
    if not FORBIDDEN_KEYWORDS:
        return False
    if not name:
        return False

    name_norm = name.lower()
    for kw in FORBIDDEN_KEYWORDS:
        if not kw:
            continue
        if kw.lower() in name_norm:
            return True
    return False