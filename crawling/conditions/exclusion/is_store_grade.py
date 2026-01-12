from selenium.webdriver.common.by import By


def get_store_grade(driver, timeout=3):
    """
    스토어 상단 오른쪽에 '스토어등급'이 있는지 확인하고 등급명을 반환.
    등급이 있으면 등급명(플래티넘, 프리미엄, 빅파워, 파워)을 반환하고,
    없으면 None을 반환.
    """
    try:
        # 스토어등급 영역 찾기
        # 예: <div class="Ypt_mSvxSl">...<span class="s3DfSDQGcc">플래티넘</span>...</div>
        grade_elements = driver.find_elements(
            By.XPATH,
            '//div[contains(@class, "Ypt_mSvxSl")]//span[contains(@class, "s3DfSDQGcc")]'
        )
        
        # 등급명 추출
        for el in grade_elements:
            text = (el.text or "").strip()
            if text in ["플래티넘", "프리미엄", "빅파워", "파워"]:
                return text
                
        return None
    except Exception:
        # 에러 발생 시 None 반환 (에러 시 통과)
        return None


def has_store_grade(driver, timeout=3):
    """
    스토어 상단 오른쪽에 '스토어등급'이 있는지 확인.
    있으면 True, 없으면 False 반환.
    (하위 호환성을 위해 유지)
    """
    grade = get_store_grade(driver, timeout)
    return grade is not None

