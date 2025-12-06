import re


def should_skip_by_category_path(category_path: str,
                                 FORBIDDEN_CATEGORY_TOKENS: set,
                                 FORBIDDEN_CATEGORY_PATHS: set) -> bool:
    if not category_path:
        return False
    if not FORBIDDEN_CATEGORY_TOKENS and not FORBIDDEN_CATEGORY_PATHS:
        return False

    normalized_path = re.sub(r"\s*>\s*", ">", category_path).strip()

    # 경로 전체 정확히 일치
    if normalized_path.casefold() in FORBIDDEN_CATEGORY_PATHS:
        return True

    parts = [p.strip() for p in normalized_path.split(">") if p.strip()]
    for p in parts:
        candidates = [p] + [x.strip() for x in re.split(r"\s*/\s*", p) if x.strip()]
        for c in candidates:
            if c.casefold() in FORBIDDEN_CATEGORY_TOKENS:
                return True

    return False



def prepare_forbidden_category_sets(FORBIDDEN_CATEGORY_KEYWORDS):
    """카테고리 금칙어를 '토큰'과 '경로(>) 포함)'로 분리해서 미리 정규화"""
    toks, paths = set(), set()

    for kw in FORBIDDEN_CATEGORY_KEYWORDS:
        kw = re.sub(r"\s*>\s*", ">", (kw or "")).strip()
        if not kw:
            continue
        if ">" in kw:   # 'A > B > C' 형태를 파일에 넣으면 '경로 전체 일치'로 처리(원하면)
            paths.add(kw.casefold())
        else:
            toks.add(kw.casefold())

    return toks, paths


