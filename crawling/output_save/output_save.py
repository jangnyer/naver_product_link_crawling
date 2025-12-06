
import pandas as pd
import os

def _move_col_to_end(df, col_name: str):
    if col_name in df.columns:
        cols = [c for c in df.columns if c != col_name] + [col_name]
        return df[cols]
    return df

def append_to_csv_incremental(records, filename):
    """
    프로그램 도중 꺼져도 남도록,
    새로 수집된 레코드를 바로바로 CSV에 추가 저장하는 함수.
    - records: [{...}, {...}] 형태
    - filename: 저장할 CSV 파일 이름
    """
    if not records:
        return

    df = pd.DataFrame(records)
    df = _move_col_to_end(df, "category_path")

    # 파일이 없으면 header 포함, 있으면 header 없이 이어쓰기
    header = not os.path.exists(filename)

    df.to_csv(
        filename,
        mode="a",              # 이어쓰기
        header=header,
        index=False,
        encoding="utf-8-sig"
    )


def save_to_excel(records, filename):
    """수집한 링크를 엑셀 파일로 저장"""
    if not records:
        print("수집된 링크가 없습니다. 엑셀을 만들지 않습니다.")
        return

    df = pd.DataFrame(records)
    df = _move_col_to_end(df, "category_path")
    df.to_excel(filename, index=False)
    print(f"엑셀 저장 완료 → {filename}")
    print(f"총 링크 개수: {len(df)}")


def save_to_csv(records, filename):
    """수집한 링크를 CSV 파일로 저장"""
    if not records:
        print("수집된 링크가 없습니다. CSV를 만들지 않습니다.")
        return

    df = pd.DataFrame(records)
    df = _move_col_to_end(df, "category_path")
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"CSV 저장 완료 → {filename}")
    print(f"총 링크 개수: {len(df)}")


def csv_to_excel(csv_filename, excel_filename, sheet_name="Sheet1"):
    if not os.path.exists(csv_filename):
        print(f"[INFO] CSV가 없어 엑셀 변환 스킵: {csv_filename}")
        return
    df = pd.read_csv(csv_filename, encoding="utf-8-sig")
    df = _move_col_to_end(df, "category_path")
    df.to_excel(excel_filename, index=False, sheet_name=sheet_name)
    print(f"엑셀 저장 완료 → {excel_filename} (rows={len(df)})")
