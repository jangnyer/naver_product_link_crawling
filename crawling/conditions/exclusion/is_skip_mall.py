
from selenium.webdriver.common.by import By


SKIP_MALL_ALTS = {
    "G마켓", "옥션", "쿠팡", "CJ온스타일", "SSG닷컴", "롯데홈쇼핑",
    "11번가", "현대Hmall", "GSSHOP", "신세계몰", "컬리", "홈앤쇼핑","롯데ON","오늘의집","삼성닷컴","지그재그",
    "삼성닷컴", "AK몰", "LF몰", "탑텐몰", "무신사", "스타일난다", "W컨셉", "29CM", "브랜디",
    "SK스토아","하이마트쇼핑몰","롯데ON","NS홈쇼핑","신세계라이브쇼핑"
}


def get_mall_name_for_link(link_element):
    """
    상품 제목/이미지 <a> 요소에서 같은 카드 안의
    대표 몰 이름(이미지 alt 또는 텍스트)을 추출.
    못 찾으면 "" 반환.
    """
    try:
        # 상품 카드(div.product_item__... 혹은 광고 카드)까지 올라가기
        card = link_element.find_element(
            By.XPATH,
            './ancestor::div[contains(@class, "product_item__") or contains(@class, "adProduct_item__")][1]'
        )
    except Exception:
        return ""

    try:
        # 카드 안에서 몰 영역 찾기
        mall_title_div = card.find_element(
            By.CSS_SELECTOR,
            'div[class^="product_mall_title__"]'
        )
    except Exception:
        return ""

    # 1순위: 이미지 alt (쿠팡, G마켓 등)
    try:
        img = mall_title_div.find_element(By.TAG_NAME, "img")
        mall_name = (img.get_attribute("alt") or "").strip()
        if mall_name:
            return mall_name
    except Exception:
        pass

    # 2순위: 텍스트
    try:
        text = mall_title_div.text.strip()
        return text
    except Exception:
        return ""


def is_skip_mall_for_link(link_element):
    """
    링크가 속한 상품 카드의 몰 이름이 SKIP_MALL_ALTS에 해당하면 True.
    (G마켓, 쿠팡, 11번가, 무신사 등 오픈마켓/제외몰 스킵용)
    """
    mall_name = get_mall_name_for_link(link_element)
    if not mall_name:
        return False

    for skip in SKIP_MALL_ALTS:
        if skip and skip in mall_name:
            print(f"[SKIP] 제외 몰({mall_name}) 상품이라 클릭하지 않음")
            return True

    return False