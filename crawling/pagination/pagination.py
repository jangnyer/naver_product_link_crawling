import time
import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

def scroll_page(driver, scroll_count=10, delay_range=(1.0, 2.0)):
    """페이지 아래로 여러 번 스크롤해서 상품 리스트 더 불러오기"""
    body = driver.find_element(By.TAG_NAME, "body")

    for i in range(scroll_count):
        body.send_keys(Keys.END)
        time.sleep(random.uniform(*delay_range))

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


def go_to_page_smart_from_first(driver, target_page, CLICK_DELAY_RANGE):
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
                    time.sleep(random.uniform(*CLICK_DELAY_RANGE))
                    return

        # 2) 아직 화면에 안 보이는 경우 → 가장 큰 번호(max_visible)를 눌러서 앞으로 크게 점프
        if max_visible < target_page:
            max_str = str(max_visible)
            print(f"타겟 {target_page}가 아직 안 보임 → {max_visible} 페이지로 점프")
            for btn in buttons:
                if btn.text.strip() == max_str:
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(random.uniform(*CLICK_DELAY_RANGE))
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
                    time.sleep(random.uniform(*CLICK_DELAY_RANGE))
                    break


def go_to_next_page(driver, CLICK_DELAY_RANGE):
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
            time.sleep(random.uniform(*CLICK_DELAY_RANGE))
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
