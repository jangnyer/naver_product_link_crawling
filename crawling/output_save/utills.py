def sanitize_filename(s: str) -> str:
    # Windows 금지 문자 제거
    bad = r'\/:*?"<>|'
    s = "".join("_" if c in bad else c for c in s).strip()
    # 끝에 점/공백 있으면 제거(윈도우에서 문제)
    return s.rstrip(" .")

def build_output_filename(prefix: str, start_page: int, end_page: int, count: int, ext: str) -> str:
    # 원하는 포맷: 사용자입력값.시작~끝.(개수).xlsx
    return f"{prefix}.{start_page}~{end_page}.({count}).{ext}"