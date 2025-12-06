import time
import random
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



START_URL = "https://search.shopping.naver.com/search/category/100000005"
SCROLL_COUNT = 5                    # 각 페이지마다 스크롤 5번
SCROLL_DELAY_RANGE = (1.0, 2.0)     # 스크롤 사이 랜덤 대기 (초)


def create_driver():
    """크롬 드라이버 생성"""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")  # 창 최대화
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def wait_for_ok():
    """
    너가 크롬에서 카테고리/필터 다 고른 뒤
    CMD에서 ok 치면 시작
    """
    user_input = input("카테고리/필터 선택 끝나면 'ok' 입력 후 엔터 → ")
    if user_input.strip().lower() != "ok":
        print("ok가 아니라서 링크 수집 없이 종료합니다.")
        return False
    return True

def ask_brand_catalog_option():
    """
    '브랜드 카탈로그'가 붙은 상품도 저장할지 여부를 y/n으로 입력받기
    """
    while True:
        s = input("브랜드 카탈로그 표시된 상품 링크도 저장할까요? (y/n) → ")
        s = s.strip().lower()

        if s in ("y", "yes", "네", "ㅇ", "응"):
            print("브랜드 카탈로그 상품도 포함해서 저장합니다.")
            return True
        if s in ("n", "no", "아니", "ㄴ", "아니오"):
            print("브랜드 카탈로그 상품은 제외하고 저장합니다.")
            return False

        print("y 또는 n으로 입력해주세요.")


def ask_page_range():
    """
    수집할 페이지 범위 입력받기 (예: 1 5, 11 15)
    """
    while True:
        s = input("수집할 페이지 범위를 입력하세요 (예: 1 5) → ")
        parts = s.strip().split()
        if len(parts) != 2:
            print("두 개의 숫자를 띄어쓰기로 입력해주세요. 예: 1 5")
            continue
        try:
            start_page = int(parts[0])
            end_page = int(parts[1])
        except ValueError:
            print("숫자로 다시 입력해주세요. 예: 1 5")
            continue

        if start_page <= 0 or end_page <= 0:
            print("페이지 번호는 1 이상이어야 합니다.")
            continue
        if end_page < start_page:
            print("끝 페이지는 시작 페이지보다 크거나 같아야 합니다.")
            continue

        return start_page, end_page


def scroll_page(driver, scroll_count=10, delay_range=(1.0, 2.0)):
    """페이지 아래로 여러 번 스크롤해서 상품 리스트 더 불러오기"""
    body = driver.find_element(By.TAG_NAME, "body")

    for i in range(scroll_count):
        body.send_keys(Keys.END)
        time.sleep(random.uniform(*delay_range))



def collect_naver_links(driver, include_brand_catalog=True):
    records = []

    # 1) 광고 영역
    ad_elements = driver.find_elements(
        By.CSS_SELECTOR,
        'div[class^="adProduct_title__"] a[class^="adProduct_link__"]'
    )
    for el in ad_elements:
        href = el.get_attribute("href")
        text = el.text.strip()

        if not href:
            continue
        if "javascript:" in href.lower():
            continue

        # 여기서 브랜드 카탈로그 판별
        is_brand = "브랜드 카탈로그" in text

        if is_brand and not include_brand_catalog:
            # 사용자가 "저장 안함" 선택한 경우 → 이 링크는 아예 무시
            continue

        records.append({
            "kind": "ad",
            "text": text,
            "href": href,
            "brand_catalog": is_brand,
        })

    # 2) 일반 상품 영역
    product_elements = driver.find_elements(
        By.CSS_SELECTOR,
        'div[class^="product_title__"] a[class^="product_link__"]'
    )
    for el in product_elements:
        href = el.get_attribute("href")
        text = el.text.strip()

        if not href:
            continue
        if "javascript:" in href.lower():
            continue

        is_brand = "브랜드 카탈로그" in text

        if is_brand and not include_brand_catalog:
            continue

        records.append({
            "kind": "product",
            "text": text,
            "href": href,
            "brand_catalog": is_brand,
        })

    # (href + kind) 기준 중복 제거
    unique = {}
    for r in records:
        key = (r["href"], r["kind"])
        unique[key] = r

    return list(unique.values())



def save_to_excel(records, filename):
    """수집한 링크를 엑셀 파일로 저장"""
    if not records:
        print("수집된 링크가 없습니다. 엑셀을 만들지 않습니다.")
        return

    df = pd.DataFrame(records)
    df.to_excel(filename, index=False)
    print(f"엑셀 저장 완료 → {filename}")
    print(f"총 링크 개수: {len(df)}")


def save_to_csv(records, filename):
    """수집한 링크를 CSV 파일로 저장"""
    if not records:
        print("수집된 링크가 없습니다. CSV를 만들지 않습니다.")
        return

    df = pd.DataFrame(records)
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"CSV 저장 완료 → {filename}")
    print(f"총 링크 개수: {len(df)}")

def wait_for_pagination(driver, timeout=10):
    """페이지네이션 영역이 DOM에 나타날 때까지 대기"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div[class^="pagination_num__"]')
            )
        )
    except Exception:
        print("[경고] 페이지네이션 영역을 찾지 못했습니다.")

def go_to_page_smart_from_first(driver, target_page, wait_sec=1.0):
    """
    1페이지에서 시작한다고 가정하고,
    보이는 페이지 번호들 중 '가장 큰 숫자' 버튼을 계속 눌러가며
    target_page에 도달할 때까지 점프하는 함수.
    예) 1 -> 10 -> 15 -> 20 -> ... -> 60
    """
    if target_page <= 1:
        return  # 이미 1페이지면 갈 필요 없음

    # 페이지네이션이 로드될 때까지 한 번 기다려줌
    wait_for_pagination(driver)

    while True:
        cur = get_current_page(driver)
        if cur is None:
            print("[경고] 현재 페이지를 찾지 못했습니다.")
            return

        if cur == target_page:
            print(f"{target_page} 페이지 도달")
            return

        if cur > target_page:
            print(f"[경고] 현재 페이지({cur})가 타겟({target_page})보다 큽니다. 중단.")
            return

        # 현재 보이는 숫자 버튼들 (pagination_num__ 안에서만 찾기)
        buttons = driver.find_elements(
            By.CSS_SELECTOR,
            'div[class^="pagination_num__"] a[class^="pagination_btn_page__"]'
        )
        nums = []
        for btn in buttons:
            txt = btn.text.strip()
            if txt.isdigit():
                nums.append(int(txt))

        if not nums:
            print("[경고] 페이지 번호 버튼을 찾지 못했습니다.")
            return

        max_visible = max(nums)

        # 1) target_page가 현재 보이는 번호들 안에 있으면 → 그 번호를 클릭하고 종료
        if target_page in nums:
            target_str = str(target_page)
            for btn in buttons:
                if btn.text.strip() == target_str:
                    print(f"{target_page} 페이지 버튼 클릭")
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(wait_sec)
                    return

        # 2) 아직 화면에 안 보이는 경우 → 가장 큰 번호(max_visible)를 눌러서 앞으로 크게 점프
        if max_visible < target_page:
            max_str = str(max_visible)
            print(f"타겟 {target_page}가 아직 안 보임 → {max_visible} 페이지로 점프")
            for btn in buttons:
                if btn.text.strip() == max_str:
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(wait_sec)
                    break
        else:
            # 안전 모드 (논리적으로 거의 안 오겠지만 방어용)
            bigger_or_equal = [n for n in nums if n >= target_page]
            if bigger_or_equal:
                click_page = min(bigger_or_equal)
            else:
                click_page = max_visible

            click_str = str(click_page)
            print(f"안전 모드: {click_page} 페이지로 이동")
            for btn in buttons:
                if btn.text.strip() == click_str:
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(wait_sec)
                    break
def go_to_next_page(driver, wait_sec=1.0):
    """
    현재 페이지에서 '다음 페이지(숫자+1)'로 이동.
    슬라이딩 페이지네이션에서도,
    pagination_num__ 안에서 active 기준으로 +1 버튼을 찾아서 클릭.
    """
    cur = get_current_page(driver)
    if cur is None:
        print("[경고] 현재 페이지를 찾지 못했습니다.")
        return

    target = cur + 1
    target_str = str(target)

    buttons = driver.find_elements(
        By.CSS_SELECTOR,
        'div[class^="pagination_num__"] a[class^="pagination_btn_page__"]'
    )
    for btn in buttons:
        if btn.text.strip() == target_str:
            print(f"{cur} -> {target} 페이지 이동")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(wait_sec)
            return

    print(f"[경고] {target} 페이지 버튼을 찾지 못했습니다. (마지막 페이지일 수 있음)")

def get_current_page(driver):
    """
    현재 활성 페이지 번호 읽기
    - div.pagination_num__ 안에서 .active 요소를 찾고
    - 그 안의 텍스트에서 숫자만 뽑아서 int로 변환
    """
    try:
        active = driver.find_element(
            By.CSS_SELECTOR,
            'div[class^="pagination_num__"] .active'
        )
        text = active.text.strip()
        # 예: "현재 페이지\n1" / "현재 페이지1" → 숫자만 추출
        digits = ''.join(ch for ch in text if ch.isdigit())
        if digits:
            return int(digits)
        return None
    except Exception:
        return None



def main():
    driver = create_driver()
    try:
        # 1) 네이버 쇼핑 카테고리 페이지 열기
        driver.get(START_URL)
        print("브라우저에서 카테고리/필터를 원하는대로 선택하세요.")

        # 2) CMD에서 ok 입력 기다리기
        if not wait_for_ok():
            return

        # 2-1) 브랜드 카탈로그 포함 여부 질문
        include_brand_catalog = ask_brand_catalog_option()


        # 3) 수집할 페이지 범위 입력받기
        start_page, end_page = ask_page_range()
        print(f">>> {start_page} 페이지부터 {end_page} 페이지까지 수집합니다.")

        # 4) 실행 시각 기준으로 파일 이름 만들기 (덮어쓰기 방지)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"naver_links_{timestamp}.xlsx"
        csv_filename = f"naver_links_{timestamp}.csv"

        # 5) 지금까지 모은 전체 링크
   
        all_records = []

        for page in range(start_page, end_page + 1):
            print("=" * 60)
            print(f"[{page} 페이지] 수집 시작")

            if page == start_page:
                # ★ 첫 페이지 이동 로직
                if page == 1:
                    print("1페이지부터 시작합니다.")
                else:
                    print(f"1페이지에서 {page}페이지로 점프합니다.")
                    go_to_page_smart_from_first(driver, page)
            else:
                # ★ 그 다음부터는 항상 '다음 페이지'만 하나씩 이동
                go_to_next_page(driver)

            # 각 페이지에서 스크롤 5번
            scroll_page(driver, SCROLL_COUNT, SCROLL_DELAY_RANGE)

            # 링크 수집
            new_links = collect_naver_links(driver, include_brand_catalog)

            print(f"[{page} 페이지] 새로 수집된 raw 링크 개수: {len(new_links)}")

            # 이전까지 모은 것 + 이번 것 합쳐서 중복 제거
            merged = {}
            for r in all_records + new_links:
                key = (r["href"], r["kind"])
                merged[key] = r
            all_records = list(merged.values())

            # 매 페이지마다 엑셀+CSV 바로 덮어쓰기 저장
            save_to_excel(all_records, excel_filename)
            save_to_csv(all_records, csv_filename)
            print(f"[{page} 페이지]까지 누적 링크 개수: {len(all_records)}")


        print("=== 모든 페이지 수집 및 최종 저장 완료 ===")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
