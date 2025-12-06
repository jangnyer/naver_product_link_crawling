import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_total_products_count(driver):
    try:
        # 네가 준 구조: span.eJTgO8xT6T 안에 strong
        el = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.eJTgO8xT6T strong"))
        )
        txt = (el.text or "").strip()          # 예: "3,192"
        digits = re.sub(r"[^\d]", "", txt)     # -> "3192" (콤마 제거)
        return int(digits) if digits else None
    except Exception:
        # strong가 없는 케이스 대비(텍스트 전체에서 뽑기)
        try:
            el2 = driver.find_element(By.CSS_SELECTOR, "span.eJTgO8xT6T")
            txt2 = (el2.text or "").strip()    # 예: "(총 3,192개)"
            m = re.search(r"총\s*([\d,]+)\s*개", txt2)
            if not m: 
                return None
            return int(m.group(1).replace(",", ""))
        except Exception:
            return None
