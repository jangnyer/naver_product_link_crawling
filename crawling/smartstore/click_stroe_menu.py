import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def click_store_menu_item(driver, text_candidates, timeout=3) -> bool:
    """
    스마트스토어 상단 메뉴(전체상품/판매자정보 등)에서 텍스트로 항목 클릭
    """
    wait = WebDriverWait(driver, timeout)

    # '더보기' 있으면 열어주기 (기존 로직 재사용 가능)
    try:
        more_btn = driver.find_element(By.XPATH, '//button[contains(normalize-space(.), "더보기")]')
        driver.execute_script("arguments[0].click();", more_btn)
        time.sleep(random.uniform(1.0, 3.0))
    except Exception:
        pass

    for t in text_candidates:
        try:
            el = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                f'//*[self::a or self::button][contains(normalize-space(.), "{t}")]'
            )))
            driver.execute_script("arguments[0].click();", el)
            time.sleep(random.uniform(1.0, 3.0))
            return True
        except Exception:
            continue
    return False
