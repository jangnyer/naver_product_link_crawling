from selenium.webdriver.common.by import By



def collect_brand_catalog_hrefs(driver) -> set:
    """현재 검색결과 페이지에서 '브랜드 카탈로그' 뱃지가 붙은 a href들을 모아서 반환"""
    brand_hrefs = set()
    try:
        em_elems = driver.find_elements(By.XPATH, '//em[contains(normalize-space(.), "브랜드 카탈로그")]')
        for em in em_elems:
            try:
                a_tag = em.find_element(By.XPATH, './ancestor::a[1]')
                href = a_tag.get_attribute("href")
                if href:
                    brand_hrefs.add(href)
            except Exception:
                pass
    except Exception:
        pass
    return brand_hrefs


def is_brand_catalog_link(el, brand_hrefs: set) -> bool:
    """상품 a 태그(el)가 브랜드 카탈로그인지 판별"""
    try:
        href = (el.get_attribute("href") or "").strip()
        text = (el.text or "").strip()
    except Exception:
        return False

    return ("브랜드 카탈로그" in text) or (href in brand_hrefs)


    