from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawling.smartstore.click_stroe_menu import click_store_menu_item
from crawling.conditions.exclusion.is_forbidden_product import is_forbidden_name

def extract_seller_info(driver, timeout=3):
    """
    판매자정보 화면에서 상호명/대표자 텍스트 추출.
    값 못 찾으면 ("","") 반환
    """
    wait = WebDriverWait(driver, timeout)
    seller_name = ""
    owner_name = ""

    try:
        # 판매자정보 영역이 뜰 때까지 dt가 보이는지 체크
        wait.until(EC.presence_of_element_located(
            (By.XPATH, '//dt[contains(normalize-space(.),"상호")]')
        ))
    except Exception:
        return "", ""

    try:
        seller_name = driver.find_element(
            By.XPATH, '//dt[contains(normalize-space(.),"상호")]/following-sibling::dd[1]'
        ).text.strip()
    except Exception:
        seller_name = ""

    try:
        owner_name = driver.find_element(
            By.XPATH, '//dt[contains(normalize-space(.),"대표")]/following-sibling::dd[1]'
        ).text.strip()
    except Exception:
        owner_name = ""

    return seller_name, owner_name


def should_skip_store_by_seller_keywords(driver, FORBIDDEN_SELLER_KEYWORDS, FORBIDDEN_OWNER_KEYWORDS):
    """
    판매자정보 탭을 열고 상호/대표자 금칙어 체크.
    항상 (skip: bool, seller_name: str) 반환
    """
    opened = click_store_menu_item(driver, ["판매자정보", "판매자 정보"])
    if not opened:
        # 판매자정보 탭이 없는 레이아웃이면 그냥 통과 (상호명도 못 얻음)
        return (False, "")

    seller_name, owner_name = extract_seller_info(driver)

    if seller_name and is_forbidden_name(seller_name, FORBIDDEN_SELLER_KEYWORDS):
        print(f"[SKIP] 상호명 금칙어 스토어 스킵: {seller_name}")
        return (True, seller_name)

    if owner_name and is_forbidden_name(owner_name, FORBIDDEN_OWNER_KEYWORDS):
        print(f"[SKIP] 대표자 금칙어 스토어 스킵: {owner_name}")
        return (True, seller_name)

    return (False, seller_name)
