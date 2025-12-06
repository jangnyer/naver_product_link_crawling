import re
from selenium.webdriver.common.by import By



def _parse_price_text(s: str):
    if not s:
        return None
    # "44,280원" / "22,990" 같은 문자열에서 숫자만
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def extract_prices_from_card(card):
    """
    card(li)에서 할인전/할인후 가격을 추출해서 (before, after) int로 반환
    - 할인 전이 없으면 before=None
    - 할인 후가 없으면 after=None
    """
    before = None
    after = None

    price_root = None
    # smartstore/brandstore에서 비교적 안정적인 price 영역 후보들
    xpaths = [
        './/*[@data-shp-area="list.priceinfo"]',
        './/div[contains(@class,"priceinfo") or contains(@class,"priceInfo")]',
        './/div[.//del][1]',  # del(할인전) 있는 블록
    ]
    for xp in xpaths:
        try:
            price_root = card.find_element(By.XPATH, xp)
            break
        except Exception:
            pass

    if price_root is None:
        return None, None

    # 1) 할인 전(있으면 del)
    try:
        del_el = price_root.find_element(By.TAG_NAME, "del")
        before = _parse_price_text(del_el.text)
    except Exception:
        before = None

    # 2) 할인 후(보통 span에 가격 숫자)
    # class가 바뀔 수 있어서 후보를 여러 개 둠
    css_candidates = [
        "span.zIK_uvWc6D",                # 질문에 나온 할인후 숫자 span
        "span[class*='price']",           # fallback
        "strong[class*='price']",         # fallback
    ]
    for css in css_candidates:
        try:
            el = price_root.find_element(By.CSS_SELECTOR, css)
            v = _parse_price_text(el.text)
            if v:
                after = v
                break
        except Exception:
            pass

    # 3) 그래도 못 찾으면, price_root 텍스트에서 '원' 근처 숫자들로 복구
    if after is None:
        nums = [int(x.replace(",", "")) for x in re.findall(r"(\d{1,3}(?:,\d{3})+|\d+)", price_root.text)]
        nums = [n for n in nums if n >= 1000]  # 평점/할인% 같은 작은 숫자 제거
        if nums:
            after = nums[-1]

    # 할인상품이 아니면 보통 after만 있고 before 없음 → before=after로 맞춰줌(필터 편함)
    if before is None and after is not None:
        before = after

    return before, after


def _price_in_range(v, min_v, max_v):
    if v is None:
        return False
    if min_v is not None and v < min_v:
        return False
    if max_v is not None and v > max_v:
        return False
    return True


def pass_price_filter(before_price, after_price,PRICE_FILTER_MODE="none", PRICE_MIN=None, PRICE_MAX=None):
    if PRICE_FILTER_MODE == "none":
        return True

    target = before_price if PRICE_FILTER_MODE == "before" else after_price
    return _price_in_range(target, PRICE_MIN, PRICE_MAX)

 
def _to_int_or_none(s):
    s = (s or "").strip()
    if not s:
        return None
    return int(re.sub(r"[^\d]", "", s))