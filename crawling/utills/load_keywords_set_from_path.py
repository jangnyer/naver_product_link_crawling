
def load_keywords_set_from_path(path: str, label: str) -> set:
    """
    ; 기준으로 키워드를 파싱해서 set으로 반환.
    path가 없으면 빈 set 반환.
    """
    if not path:
        # gui_log(f"[INFO] {label} 파일 미사용")
        return set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        # gui_log(f"[WARN] {label} 파일을 읽지 못했습니다: {e}")
        return set()

    raw_parts = []
    for line in text.splitlines():
        raw_parts.extend(line.split(";"))

    words = {p.strip() for p in raw_parts if p.strip()}
    # gui_log(f"[INFO] {label} {len(words)}개 로드 완료")
    return words

