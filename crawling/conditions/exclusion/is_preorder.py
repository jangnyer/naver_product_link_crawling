from selenium.webdriver.common.by import By


def is_preorder_product_link(link_element):
    """
    카테고리(검색) 페이지에서:
    - 상품 제목 영역(div.product_title__ 또는 div.adProduct_title__) 안에
    - '예약구매'라고 적힌 button이 있으면 True 반환 (수집에서 제외)

    link_element: 검색결과의 <a> 태그 (product_link__*, adProduct_link__* 등)
    """
    try:
        # 이 링크가 속한 제목 영역 div (상품/광고 둘 다 대응)
        title_div = link_element.find_element(
            By.XPATH,
            './ancestor::div[contains(@class, "product_title__") or contains(@class, "adProduct_title__")][1]'
        )
    except Exception:
        # 제목 영역을 못 찾으면 그냥 예약구매로 보지 않음
        return False

    try:
        # 제목 영역 안의 모든 버튼 텍스트 확인
        buttons = title_div.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            text = (btn.text or "").strip()
            if "예약구매" in text:
                try:
                    name = (link_element.get_attribute("title") or link_element.text or "").strip()
                except Exception:
                    name = ""
                print(f"[SKIP] 예약구매 상품이라 수집하지 않음: {name}")
                return True
    except Exception:
        pass

    return False
