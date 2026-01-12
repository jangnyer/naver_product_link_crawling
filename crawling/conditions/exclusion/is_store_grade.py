from selenium.webdriver.common.by import By


def has_store_grade(driver, timeout=3):
    """
    스토어 상단 오른쪽에 '스토어등급'이 있는지 확인.
    있으면 True, 없으면 False 반환.
    """
    try:
        # 스토어등급 텍스트가 있는 span 요소 찾기
        # 예: <span class="BQx5V3JBXv">스토어등급</span>
        elements = driver.find_elements(
            By.XPATH,
            '//span[contains(normalize-space(), "스토어등급")]'
        )
        
        # 스토어등급 텍스트가 있는지 확인
        for el in elements:
            text = (el.text or "").strip()
            if "스토어등급" in text:
                return True
                
        return False
    except Exception:
        # 에러 발생 시 False 반환 (에러 시 통과)
        return False

