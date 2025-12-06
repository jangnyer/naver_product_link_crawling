from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def is_ad_link(el) -> str:
    """상품 a 태그(el)가 광고 영역이면 'ad', 아니면 'product'"""
    try:
        # 광고는 보통 adProduct_ 계열 컨테이너 안에 있음
        el.find_element(By.XPATH, 'ancestor::div[starts-with(@class,"adProduct_")]')
        return "ad"
    except NoSuchElementException:
        return "product"
    except Exception:
        return "product"