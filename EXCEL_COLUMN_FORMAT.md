# Excel 저장 컬럼 형식

이 프로그램을 실행하면 Excel 파일에 다음과 같은 컬럼 형식으로 저장됩니다.

## 컬럼 순서 및 설명

| 순서 | 컬럼명 | 설명 | 예시 |
|------|--------|------|------|
| 1 | `href` | 상품 링크 URL | `https://smartstore.naver.com/earphoneshop/products/12111211905` |
| 2 | `kind` | 상품 종류 | `ad` (광고) 또는 `product` (일반 상품) |
| 3 | `text` | 상품명 | `젠하이저 BTD700 블루투스 동글 어댑터` |
| 4 | `brand_catalog` | 브랜드 카탈로그 여부 | `True` 또는 `False` |
| 5 | `store` | 스토어 키 (도메인/첫번째 경로) | `smartstore.naver.com/earphoneshop` |
| 6 | `store_name` | 스토어 이름 | `이어폰샵` |
| 7 | `price_before` | 할인 전 가격 (원) | `64900` |
| 8 | `price_after` | 할인 후 가격 (원) | `64900` |
| 9 | `category_path` | 카테고리 경로 | `디지털/가전 > 음향가전 > 헤드폰` |

## 주의사항

- **`category_path` 컬럼은 항상 마지막에 배치됩니다.** (`_move_col_to_end` 함수에 의해 처리됨)
- 가격 정보가 없는 경우 `price_before`와 `price_after`는 빈 값 또는 `None`일 수 있습니다.
- `brand_catalog`는 불린 값이지만 Excel에서는 `True`/`False`로 표시됩니다.

## 실제 예시

```csv
href,kind,text,brand_catalog,store,store_name,price_before,price_after,category_path
https://smartstore.naver.com/earphoneshop/products/12111211905,ad,젠하이저 BTD700 블루투스 동글 어댑터,False,smartstore.naver.com/earphoneshop,이어폰샵,64900,64900,디지털/가전 > 음향가전 > 헤드폰
```

## 관련 코드 위치

- 컬럼 정의: `main.py`의 `collect_best_from_current_store` 함수 (829-839줄, 844-854줄)
- Excel 저장: `crawling/output_save/output_save.py`의 `save_to_excel` 함수 (36-46줄)
- 컬럼 순서 조정: `crawling/output_save/output_save.py`의 `_move_col_to_end` 함수 (5-9줄)


