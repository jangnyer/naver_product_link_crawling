#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 저장 컬럼 형식 확인 스크립트
실제 프로그램이 저장하는 Excel 파일의 컬럼 구조를 확인합니다.
"""

import pandas as pd
from crawling.output_save.output_save import save_to_excel, _move_col_to_end

# 샘플 데이터 생성 (실제 프로그램이 저장하는 형식과 동일)
sample_records = [
    {
        "href": "https://smartstore.naver.com/earphoneshop/products/12111211905",
        "kind": "ad",
        "text": "젠하이저 BTD700 블루투스 동글 어댑터",
        "brand_catalog": False,
        "store": "smartstore.naver.com/earphoneshop",
        "store_name": "이어폰샵",
        "category_path": "디지털/가전 > 음향가전 > 헤드폰",
        "price_before": 64900,
        "price_after": 64900,
    },
    {
        "href": "https://smartstore.naver.com/nobletrio/products/9755601129",
        "kind": "product",
        "text": "수능 모의고사답지 모의고사 준비 연습 OMR카드 오엠알",
        "brand_catalog": False,
        "store": "smartstore.naver.com/nobletrio",
        "store_name": "마켓 노트",
        "category_path": "생활/건강 > 수집품 > 게임 > 보드게임",
        "price_before": 2500,
        "price_after": 1750,
    },
]

# DataFrame 생성 (실제 프로그램과 동일한 로직)
df = pd.DataFrame(sample_records)
df = _move_col_to_end(df, "category_path")

print("=" * 80)
print("Excel 저장 컬럼 형식")
print("=" * 80)
print()
print("컬럼 순서:")
print("-" * 80)
for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")
print()
print("=" * 80)
print("샘플 데이터 (처음 2행):")
print("=" * 80)
print()
print(df.to_string(index=False))
print()
print("=" * 80)
print("컬럼 상세 정보:")
print("=" * 80)
print()
for col in df.columns:
    dtype = df[col].dtype
    print(f"  {col:20s} : {str(dtype):15s} (예: {df[col].iloc[0]})")
print()
print("=" * 80)
print("참고: category_path 컬럼은 항상 마지막에 배치됩니다.")
print("=" * 80)


