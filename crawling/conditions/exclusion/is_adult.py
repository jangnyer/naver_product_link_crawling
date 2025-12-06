from selenium.webdriver.common.by import By

def is_adult_product_element(link_element):
    """
    검색결과의 제목/이미지 <a> 요소에서
    같은 상품 카드 안에 '청소년 유해상품' 배지가 있는지 확인해서
    19금이면 True, 아니면 False 리턴
    """
    try:
        # 이 a 태그가 속한 상품 카드(div.product_item__...)까지 위로 올라가기
        card = link_element.find_element(
            By.XPATH,
            './ancestor::div[contains(@class, "product_item__")][1]'
        )
    except Exception:
        # 상품 카드 구조 아니면 그냥 성인상품 아님 처리
        return False

    # 1) class 이름으로 성인 배지 찾기
    try:
        card.find_element(By.CSS_SELECTOR, 'span[class^="adultBlock_teenager__"]')
        return True
    except Exception:
        pass

    # 2) 시각장애인용 텍스트 '청소년 유해상품' 찾기 (안전망)
    try:
        blind_spans = card.find_elements(By.CSS_SELECTOR, 'span.blind')
        for sp in blind_spans:
            if "청소년 유해상품" in (sp.text or ""):
                return True
    except Exception:
        pass

    return False
