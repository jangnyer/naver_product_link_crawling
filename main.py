import random
import os
import time
import re
import tkinter as tk
import threading
import sys, json, traceback
import shutil
from tkinter import ttk,messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin  
from urllib.parse import urlparse  
from selenium.common.exceptions import NoSuchElementException
from openai import OpenAI
from selenium.common.exceptions import WebDriverException
from tkinter import filedialog

from selenium.common.exceptions import NoSuchWindowException


from captcha.captcha import (
    handle_captcha_if_needed,
)

from captcha.api import (
    save_api_key_to_file,
    load_saved_api_key
)
from crawling.pagination.pagination import (
    go_to_next_page,
    go_to_page_smart_from_first,
    scroll_page
)
from crawling.output_save.output_save import (
    append_to_csv_incremental,
    save_to_excel,
    save_to_csv,
)

from crawling.conditions.exclusion.is_preorder import (
    is_preorder_product_link
)

from crawling.conditions.exclusion.is_adult import(
    is_adult_product_element
)
from crawling.conditions.exclusion.is_skip_mall import(    
    is_skip_mall_for_link
)
from crawling.conditions.exclusion.is_forbidden_product import(
    is_forbidden_name
)
from crawling.conditions.filter.is_brand_catalog import(
    collect_brand_catalog_hrefs,
    is_brand_catalog_link
)
from crawling.conditions.filter.is_add import(
    is_ad_link
)
from crawling.conditions.exclusion.is_forbidden_seller import(
    should_skip_store_by_seller_keywords
)
from crawling.utills.load_keywords_set_from_path import(   
    load_keywords_set_from_path
)
from crawling.output_save.utills import(
    sanitize_filename,
    build_output_filename
)
from crawling.conditions.exclusion.is_total_count import(
    extract_total_products_count
)
from crawling.conditions.utils import(
    get_store_home_url,
    get_store_name_fallback
)
from crawling.conditions.exclusion.is_forbidden_category import(
    should_skip_by_category_path,
    prepare_forbidden_category_sets
)

import crawling.conditions.filter.price as price

from crawling.conditions.filter.price import (
    pass_price_filter,
    _to_int_or_none,
)

from crawling.output_save.exist_results import(
    load_hrefs_from_many,
    normalize_href
)


SKIP_MALL_ALTS = {
    "G마켓", "옥션", "쿠팡", "CJ온스타일", "SSG닷컴", "롯데홈쇼핑",
    "11번가", "현대Hmall", "GSSHOP", "신세계몰", "컬리", "홈앤쇼핑","롯데ON","오늘의집","삼성닷컴","지그재그",
    "삼성닷컴", "AK몰", "LF몰", "탑텐몰", "무신사", "스타일난다", "W컨셉", "29CM", "브랜디",
    "SK스토아","하이마트쇼핑몰","롯데ON","NS홈쇼핑","신세계라이브쇼핑"
}
# 이미 BEST를 수집해서 방문한 스마트스토어/브랜드스토어 키
VISITED_STORE_KEYS = set()
FORBIDDEN_PRODUCT_KEYWORDS = set()
FORBIDDEN_SELLER_KEYWORDS = set()   # 상호명 금칙어
FORBIDDEN_OWNER_KEYWORDS  = set()   # 대표자 금칙어
FORBIDDEN_CATEGORY_KEYWORDS = set()  # 카테고리 금칙어
FORBIDDEN_CATEGORY_TOKENS = set()  # 예: {"마이크", "음향가전"}
FORBIDDEN_CATEGORY_PATHS  = set()  # 예: {"디지털/가전>음향가전>마이크"} (옵션)
FORBIDDEN_BRAND_KEYWORDS = set()


START_URL = "https://search.shopping.naver.com/search/category/100000005"
SCROLL_COUNT = 5                    # 각 페이지마다 스크롤 5번
SCROLL_DELAY_RANGE = (1.5, 3.0)     # 스크롤 사이 랜덤 대기 (초)

# 👇 클릭 후 기다리는 시간 범위(초) – 필요하면 숫자만 바꿔서 튜닝
CLICK_DELAY_RANGE = (3.0, 7.0)

client = None
MAX_RETRY = 10  # 최대 재시도 횟수

API_KEY_FILE = "openai_api_key.txt"  # 같은 폴더에 저장될 파일 이름

client = None
api_key = ""

PRICE_MODE = "none"
PRICE_MIN = None
PRICE_MAX = None

EXISTING_HREFS = set()
existing_result_paths_var = None  # tk.Variable로 나중에 생성

# 브랜드 카탈로그 모드: "all" / "first" / "none"
BRAND_CATALOG_MODE = "all"

# ---- 크롤러/GUI 공유 상태 ----
driver = None          # 크롬 드라이버 인스턴스
crawl_thread = None    # 백그라운드 수집 쓰레드
STOP_REQUESTED = False # 중단 요청 플래그
forbidden_path_var = None  # 금칙어 파일 경로 (나중에 초기화)
client = None   # ← 여기까지만


EXCLUDE_CUSTOM = False          # 맞춤제작 상품 제외 여부
EXCLUDE_OVERSEAS = False        # 해외직배송 상품 제외 여부
EXCLUDE_PREORDER_DETAIL = False # (상세페이지 기준) 예약구매 상품 제외 여부


STORE_COLLECT_MODE = "best"  # "best" or "all"

STOP_REQUESTED = False # 중단 요청 플래그
forbidden_path_var = None  # 금칙어 파일 경로 (나중에 초기화)
client = None   # ← 여기까지만

# ================= 재시작(이어하기)용 전역 상태 =================
RESUME_STATE_FILE = "crawl_resume_state.txt"  # 마지막 완료 페이지 저장용
ORIG_START_PAGE = None  # 처음 사용자가 입력한 시작 페이지
ORIG_END_PAGE = None    # 처음 사용자가 입력한 끝 페이지
LAST_FINISHED_PAGE = 0  # 마지막으로 "완전히 끝난" 페이지 번호
# ===========================================================

EXCLUDE_CUSTOM = False          # 맞춤제작 상품 제외 여부
EXCLUDE_OVERSEAS = False        # 해외직배송 상품 제외 여부
EXCLUDE_PREORDER_DETAIL = False # (상세페이지 기준) 예약구매 상품 제외 여부

CATEGORY_URL = None   # 사용자가 필터 고른 "카테고리 검색결과" URL
# ---- 크롤러/GUI 공유 상태 ----
STOP_REQUESTED = False  # 중단 요청 플래그

start_fresh_btn = None
start_resume_btn = None


# 상품 상세페이지 네이버 버그 보류 목록
PENDING_RECHECK = []     # 나중에 다시 확인해야 할 URL들
FAIL_RECORDS   = []      # 정상적으로 열리지 않는 URL들



def should_stop():
    global STOP_REQUESTED
    if STOP_REQUESTED:
        print("[STOP] 사용자 중단 요청 감지 → 즉시 중단")
        return True
    return False
def prune_debug_runs(base_dir, keep=5):
    try:
        if not os.path.isdir(base_dir):
            return
        dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir)]
        dirs = [d for d in dirs if os.path.isdir(d)]
        dirs.sort(key=lambda p: os.path.getmtime(p))  # 오래된 순

        while len(dirs) > keep:
            old = dirs.pop(0)
            try:
                shutil.rmtree(old, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        pass


APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

def make_run_dir():
    base = os.path.join(APP_DIR, "debug_runs")
    os.makedirs(base, exist_ok=True)

    prune_debug_runs(base, keep=5)  # ✅ 먼저 오래된 폴더 정리

    run_dir = os.path.join(base, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    return run_dir

RUN_DIR = make_run_dir()
LOG_FILE = os.path.join(RUN_DIR, "console.log")

class Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            try: s.write(data)
            except: pass
        for s in self.streams:
            try: s.flush()
            except: pass
    def flush(self):
        for s in self.streams:
            try: s.flush()
            except: pass

# stdout/stderr를 파일로도 저장
_log_fp = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
sys.stdout = Tee(sys.__stdout__, _log_fp)
sys.stderr = Tee(sys.__stderr__, _log_fp)


def normalize_tabs_to_main(driver):
    try:
        handles = driver.window_handles
        if not handles:
            return
        main = handles[0]
        # 메인으로 이동
        driver.switch_to.window(main)
        # 나머지 탭 닫기
        for h in handles[1:]:
            try:
                driver.switch_to.window(h)
                driver.close()
            except Exception:
                pass
        driver.switch_to.window(main)
    except Exception:
        pass


def dump_debug_bundle(driver, tag="error"):
    """
    문제 발생 시 RUN_DIR 아래에 스크린샷/HTML/메타정보/브라우저 콘솔 로그 저장
    """
    ts = datetime.now().strftime("%H%M%S")
    meta_path = os.path.join(RUN_DIR, f"{tag}_{ts}_meta.json")
    html_path = os.path.join(RUN_DIR, f"{tag}_{ts}.html")
    png_path  = os.path.join(RUN_DIR, f"{tag}_{ts}.png")
    blog_path = os.path.join(RUN_DIR, f"{tag}_{ts}_browser.log")

    meta = {}
    try:
        meta["current_url"] = driver.current_url if driver else None
        meta["window_handles"] = driver.window_handles if driver else []
        meta["current_handle"] = driver.current_window_handle if driver else None
    except Exception:
        pass

    try:
        if driver:
            driver.save_screenshot(png_path)
    except Exception:
        pass

    try:
        if driver:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
    except Exception:
        pass

    # 크롬 브라우저 콘솔 로그(가능한 경우)
    try:
        if driver:
            logs = driver.get_log("browser")
            with open(blog_path, "w", encoding="utf-8") as f:
                for row in logs:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass

    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    print(f"[DEBUG] 디버그 번들 저장 완료: {RUN_DIR}")

def save_resume_state(orig_start, orig_end, last_finished, category_url=None):
    """
    재시작 정보를 텍스트 파일로 저장.
    1) orig_start
    2) orig_end
    3) last_finished
    4) category_url (없으면 빈 문자열)
    """
    try:
        with open(RESUME_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(f"{orig_start}\n{orig_end}\n{last_finished}\n")
            f.write((category_url or "") + "\n")
    except Exception as e:
        print(f"[WARN] 재시작 정보 저장 실패: {e}")

def load_resume_state():
    if not os.path.exists(RESUME_STATE_FILE):
        return None
    try:
        with open(RESUME_STATE_FILE, "r", encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f.readlines()]

        # 예전(3줄) 포맷도 호환
        if len(lines) < 3:
            return None

        s = int(lines[0].strip())
        e = int(lines[1].strip())
        last = int(lines[2].strip())
        category_url = lines[3].strip() if len(lines) >= 4 else ""

        return {
            "orig_start": s,
            "orig_end": e,
            "last_finished": last,
            "category_url": category_url,
        }
    except Exception:
        return None

def start_collect(use_resume=True):
    global STOP_REQUESTED, crawl_thread, CLICK_DELAY_RANGE, api_key, client, driver
    global PRICE_MODE, PRICE_MIN, PRICE_MAX 


    output_name= output_name_var.get().strip()
    category_forbidden_path = category_forbidden_path_var.get().strip() or None

    mode = price_filter_var.get()
    try:
        min_v = _to_int_or_none(price_min_var.get())
        max_v = _to_int_or_none(price_max_var.get())
    except Exception:
        messagebox.showerror("입력 오류", "가격 범위는 숫자(원)로 입력해주세요.")
        return

    # ✅ 가격 필터 검증
    if mode != "none":
        if min_v is None and max_v is None:
            mode = "none"
        elif min_v is not None and max_v is not None and max_v < min_v:
            messagebox.showerror("입력 오류", "가격 범위에서 '까지' 값이 '부터' 값보다 작아요.")
            return

    # ✅ 전역에 저장 (다른 함수에서 쓰려고)
    PRICE_MODE = mode
    PRICE_MIN = min_v
    PRICE_MAX = max_v

    if driver is None:
        messagebox.showerror("에러", "먼저 [카테고리 필터 선택]으로 크롬을 열어주세요.")
        return

        # 🔍 크롬 창이 아직 살아있는지 확인
    try:
        _ = driver.current_url  # 창이 닫혔으면 여기서 예외 발생
    except WebDriverException:
        messagebox.showerror(
            "에러",
            "크롬 창이 이미 닫혀 있습니다.\n"
            "[카테고리 필터 선택] 버튼을 눌러 크롬을 다시 연 뒤,\n"
            "카테고리를 다시 선택하고 수집을 시작해주세요."
        )
        return


    global CATEGORY_URL
    try:
        CATEGORY_URL = driver.current_url  # 사용자가 필터 고른 최종 상태 URL
        # gui_log(f"[INFO] 카테고리 기준 URL 저장: {CATEGORY_URL}")
    except Exception:
        CATEGORY_URL = None

    # ✅ 0) API Key 읽어서 client 생성
    api_key = key_entry.get().strip()
    if not api_key:
        messagebox.showerror("입력 오류", "먼저 API Key를 입력해주세요.")
        return

    try:
        client = OpenAI(api_key=api_key)
        save_api_key_to_file(api_key)
        gui_log("[INFO] OpenAI API Key 설정 완료")
    except Exception as e:
        messagebox.showerror("API 에러", f"API Key 설정 중 오류: {e}")
        return

    # 1) 페이지 범위
    try:
        start_page = int(start_page_var.get())
        end_page   = int(end_page_var.get())
    except Exception:
        messagebox.showerror("입력 오류", "시작/끝 페이지는 숫자로 입력해주세요.")
        return

    if start_page <= 0 or end_page < start_page:
        messagebox.showerror("입력 오류", "페이지 범위를 다시 확인해주세요.")
        return

    # 🔹 원래 사용자가 입력한 범위(재시작용 전역)에 저장
    global ORIG_START_PAGE, ORIG_END_PAGE
    ORIG_START_PAGE = start_page
    ORIG_END_PAGE   = end_page

    # 🔹 이전 실행에서 저장된 재시작 정보가 있으면, 그 다음 페이지부터 이어서 시작
    if use_resume:
        resume_info = load_resume_state()
        if resume_info and resume_info["orig_start"] == ORIG_START_PAGE and resume_info["orig_end"] == ORIG_END_PAGE:
            resume_from = resume_info["last_finished"]
            if resume_from <= end_page:
                gui_log(f"[RESUME] 이전 실행에서 {resume_info['last_finished']} 페이지까지 완료 → {resume_from} 페이지부터 이어서 시작합니다.")
                start_page = resume_from
            else:
                gui_log("[RESUME] 저장된 재시작 정보가 범위를 벗어나서 무시합니다.")
        else:
            save_resume_state(ORIG_START_PAGE, ORIG_END_PAGE, ORIG_START_PAGE - 1)
    else:
        # ✅ 새로 시작은 무조건 '기록 새로 세팅'
        save_resume_state(ORIG_START_PAGE, ORIG_END_PAGE, ORIG_START_PAGE - 1)



            
    # 2) 브랜드 카탈로그 모드 (all / first / none)
    brand_catalog_mode = link_option_var.get()  # "all" / "first" / "none"
     # ⭐ 2-1) 광고 포함 여부 
    include_ads = (ad_option_var.get() == "include")


    # ⭐ 2-3) 상세 필터 (맞춤제작 / 해외직배송 / 예약구매)
    exclude_custom = exclude_custom_var.get()
    exclude_overseas = exclude_overseas_var.get()
    exclude_preorder_detail = exclude_preorder_detail_var.get()

    store_collect_mode = store_collect_var.get()


    # 3) 클릭 간격
    try:
        min_click = float(min_click_sec_var.get())
        max_click = float(max_click_sec_var.get())
        if min_click < 0 or max_click < min_click:
            raise ValueError
    except Exception:
        messagebox.showerror("입력 오류", "클릭 간격(최소/최대)을 올바르게 입력해주세요.")
        return

    CLICK_DELAY_RANGE = (min_click, max_click)

    prefix = sanitize_filename(output_name) or "naver_links"

    # 4) 금칙어 파일 경로
    forbidden_file_path = forbidden_path_var.get().strip() or None
    seller_forbidden_path = seller_forbidden_path_var.get().strip() or None
    owner_forbidden_path  = owner_forbidden_path_var.get().strip() or None

    try:
        total_limit = int(total_product_limit.get())
        if total_limit <= 0:
            total_limit = None
    except Exception:
        messagebox.showerror("입력 오류", "전체상품 기준 개수는 숫자로 입력해주세요.")
        return
    
    # 5) 이미 돌고 있는지 체크
    if crawl_thread is not None and crawl_thread.is_alive():
        messagebox.showwarning("알림", "이미 수집이 진행 중입니다.")
        return

        # ✅ 기존 결과 엑셀들에서 href 로드 (중복 제외용)
    global EXISTING_HREFS
    EXISTING_HREFS = set()

    paths = []
    try:
        paths = list(existing_result_paths_var.get()) if existing_result_paths_var else []
    except Exception:
        paths = []

    if paths:
        hrefs, used, errors = load_hrefs_from_many(paths, max_files=100, href_col=1)
        if errors:
            # 에러가 있어도 진행할지/막을지는 선택
            # 여기서는 "에러가 있으면 막기"로 해둘게 (안전)
            msg = "\n".join([f"- {p} ({reason})" for p, reason in errors[:10]])
            if len(errors) > 10:
                msg += f"\n... 외 {len(errors)-10}개"
            messagebox.showerror("엑셀 로드 오류", f"기존 결과 엑셀 로딩 중 오류:\n{msg}")
            return

        EXISTING_HREFS = hrefs
        gui_log(f"[INFO] 기존 엑셀 {len(used)}개에서 href {len(EXISTING_HREFS)}개 로드 완료 → 중복 제외 적용")

    STOP_REQUESTED = False
    # 시작 버튼 2개 비활성화
    if start_fresh_btn is not None:
        start_fresh_btn.config(state="disabled")
    if start_resume_btn is not None:
        start_resume_btn.config(state="disabled")

    stop_button.config(state="normal")


    # 브랜드 카탈로그 모드 설명용 텍스트
    if brand_catalog_mode == "all":
        bc_desc = "브랜드카탈로그: 스마트스토어 모두 수집"
    elif brand_catalog_mode == "first":
        bc_desc = "브랜드카탈로그: 첫 번째 스마트스토어만 수집"
    else:
        bc_desc = "브랜드카탈로그: 수집 안 함"

    gui_log(f"[INFO] 수집 시작: {start_page}~{end_page}페이지 / {bc_desc}")

    def worker():
        try:
            run_crawler(
                start_page, 
                end_page, 
                brand_catalog_mode, 
                forbidden_file_path,
                seller_forbidden_path,
                owner_forbidden_path,
                category_forbidden_path=category_forbidden_path,
                brand_forbidden_path=brand_forbidden_path_var.get().strip() or None,
                include_ads=include_ads,
                api_key=api_key,
                output_name=output_name,
                total_product_limit=total_limit,
                price_mode=mode,
                price_min=min_v,
                price_max=max_v,
                exclude_custom=exclude_custom,
                exclude_overseas=exclude_overseas,
                exclude_preorder_detail=exclude_preorder_detail,
                store_collect_mode=store_collect_mode,
            )

        except Exception as e:
            print("[FATAL] 크롤러 예외 발생:", repr(e))
            traceback.print_exc()
            dump_debug_bundle(driver, tag="fatal")
            raise

        finally:
            def _enable_buttons():
                if start_fresh_btn is not None:
                    start_fresh_btn.config(state="normal")
                if start_resume_btn is not None:
                    start_resume_btn.config(state="normal")
                stop_button.config(state="disabled")

            root.after(0, _enable_buttons)

    crawl_thread = threading.Thread(target=worker, daemon=True)
    crawl_thread.start()

def stop_collect():
    global STOP_REQUESTED, crawl_thread, driver

    if crawl_thread is None or not crawl_thread.is_alive():
        messagebox.showinfo("중단", "현재 실행 중인 수집 작업이 없습니다.")
        return

    STOP_REQUESTED = True
    gui_log("[INFO] 중단 요청을 보냈습니다. 잠시만 기다려주세요...")

    # 🔹 로딩 중이면 네트워크 정지 (가능하면 바로 멈추게)
    try:
        if driver is not None:
            driver.execute_script("window.stop();")
            normalize_tabs_to_main(driver)
    except Exception:
        pass

def is_product_not_exist(driver):
    """
    상세 페이지에서 네이버 쇼핑 버그로 '상품이 존재하지 않습니다'가 뜨는지 검사
    """
    try:
        txt = driver.page_source
        if "상품이 존재하지 않습니다" in txt:
            return True
    except Exception:
        pass
    return False


def gui_log(msg: str):
    print(msg)
    try:
        log_text.insert("end", msg + "\n")
        log_text.see("end")
    except Exception:
        pass


def get_store_key(url: str) -> str:
    """
    smartstore / brandstore URL에서
    '도메인/첫번째 path 조각'만 떼어서 스토어를 대표하는 키로 사용
    """
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").strip("/")
        first = path.split("/", 1)[0] if path else ""
        return f"{parsed.netloc}/{first}"
    except Exception:
        return url


def collect_best_products_on_all_products_page(driver):
    """
    현재 페이지(전체상품 페이지)에서 BEST 뱃지가 붙은 상품들을 수집.
    브랜드스토어/스마트스토어의 리스트형, 그리드형 구조를 모두 대응하도록 개선함.
    """
    if should_stop():
        return []
    best_items = []
    seen_hrefs = set()
    
    # 1. BEST 뱃지가 포함된 모든 '상품 카드(li)'를 먼저 찾습니다.
    # (BEST 뱃지가 있는 em의 조상 중 li 태그를 찾음)
    product_cards = driver.find_elements(
        By.XPATH,
        '//li[descendant::em[contains(normalize-space(.), "BEST")]]'
    )

    print(f"[DEBUG] BEST 뱃지가 있는 상품 카드 {len(product_cards)}개 발견")

    for card in product_cards:
        if should_stop():
            break
        # --- 0. 🔞 청소년 유해상품 마크 확인 및 건너뛰기 ---
        try:
            # 'adultBlock_teenager__iVi6S' 클래스를 가진 요소를 찾습니다.
            # 요소가 발견되면 19금 상품입니다.
            card.find_element(By.CLASS_NAME, "adultBlock_teenager__iVi6S")
            
            # 19금 마크가 발견된 경우, 상품명을 추출하여 출력하고 건너뜁니다.
            try:
                # 상품명은 출력용으로만 사용 (추출 실패해도 상관없음)
                product_name = card.find_element(By.XPATH, './/a[contains(@href, "/products/")]').get_attribute("title")
            except NoSuchElementException:
                product_name = "이름을 찾을 수 없는 상품"
                
            print(f"[SKIP] 목록에서 19금 상품 마크 확인: {product_name}")
            continue # 19금 상품이므로 다음 상품으로 넘어갑니다.
            
        except NoSuchElementException:
            # 'adultBlock_teenager__iVi6S' 요소가 없으면, 19금 상품이 아니므로 통과
            pass
        # -------------------------------------------------------------------

        try:
            # 2. 링크(href) 추출
            # 카드 내부에서 /products/가 포함된 a 태그를 찾음
            try:
                link_element = card.find_element(By.XPATH, './/a[contains(@href, "/products/")]')
                raw_href = link_element.get_attribute("href")
            except Exception:
                continue # 링크 없으면 스킵

            if not raw_href:
                continue
                
            # 상대 경로일 경우 절대 경로로 변환
            href = urljoin(driver.current_url, raw_href)
            href = normalize_href(href)

            if href in EXISTING_HREFS:
                print(f"[SKIP] 기존 결과에 이미 있는 href: {href}")
                continue

            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            # 3. 상품명(Title) 추출
            title = ""
            try:
                # strong 태그 우선 검색
                title_el = card.find_element(By.TAG_NAME, "strong")
                title = title_el.text.strip()
            except Exception:
                # 실패 시 이미지의 alt 속성 시도
                try:
                    img = card.find_element(By.TAG_NAME, "img")
                    title = img.get_attribute("alt").strip()
                except:
                    title = "제목 없음"

            # 금지어 체크 (기존 로직)
            if is_forbidden_name(title, FORBIDDEN_PRODUCT_KEYWORDS):
                print(f"[SKIP] 금지어 포함 상품 스킵: {title}")
                continue

            before_price, after_price = price.extract_prices_from_card(card)

            if not pass_price_filter(before_price, after_price, PRICE_MODE, PRICE_MIN, PRICE_MAX):
                print(f"[SKIP] 가격 필터 스킵: mode={PRICE_MODE}, min={PRICE_MIN}, max={PRICE_MAX}, before={before_price}, after={after_price}, title={title}")
                continue


            best_items.append({
                "href": href,
                "text": title,
                "price_before": before_price,
                "price_after": after_price,
            })
            
        except Exception as e:
            # BEST 뱃지 외에 다른 이유로 파싱 실패 시
            print(f"[ERROR] 상품 파싱 중 오류: {e}")
            continue

    print(f"[INFO] 전체상품 페이지에서 BEST {len(best_items)}개 수집 완료")
    return best_items

def collect_best_from_current_store(driver, base_kind, is_brand_catalog,
                                    total_product_limit=None, record_oversize_store=None, category_path=""):
    # 0) 어떤 페이지(상품 상세)로 들어와도 스토어 홈으로 정렬
    home_url = get_store_home_url(driver.current_url)
    if home_url != driver.current_url:
        driver.get(home_url)
        time.sleep(random.uniform(*CLICK_DELAY_RANGE))

    store_key = get_store_key(driver.current_url)
    if store_key in VISITED_STORE_KEYS:
        print(f"[SKIP] 이미 BEST를 수집한 스토어입니다: {store_key}")
        return []
    VISITED_STORE_KEYS.add(store_key)
    print(f"[STORE] 새 스토어 진입 → {store_key}")

    need_seller_filter = bool(FORBIDDEN_SELLER_KEYWORDS) or bool(FORBIDDEN_OWNER_KEYWORDS)
    seller_name = ""

    # 1) 금칙어 파일이 있을 때만 판매자정보 들어가서 체크
    if need_seller_filter:
        skip_by_kw, seller_name = should_skip_store_by_seller_keywords(
            driver, FORBIDDEN_SELLER_KEYWORDS, FORBIDDEN_OWNER_KEYWORDS
        )
        if skip_by_kw:
            return []

    # 2) 전체상품 이동
    go_to_all_products_if_exists(driver)

    # ✅ 여기서 스토어 이름 한 번만 추출
    store_name = get_store_name_fallback(driver)

    # 3) 전체상품 개수 체크
    if total_product_limit is not None:
        total_cnt = extract_total_products_count(driver)
        print("[DEBUG] total_cnt raw =", total_cnt, "limit =", total_product_limit)
        if total_cnt is not None and total_cnt >= total_product_limit:

            # ✅ 금칙어 체크를 안 했던 케이스(=seller_name 없음)면, 초과일 때만 판매자정보 들어가서 상호명 확보
            if not seller_name:
                _skip, seller_name = should_skip_store_by_seller_keywords(
                    driver, set(), set()   # 금칙어 없지만 "상호명만" 뽑기 용도
                )

            rec = {
                "store_url": get_store_home_url(driver.current_url),
                "store_name": store_name,   # ← 여기도 동일한 store_name 사용
                "seller_name": seller_name,
                "total_products": total_cnt,
                "category_path": category_path
            }
            if record_oversize_store:
                record_oversize_store(rec)
            return []

    # 4) BEST 수집
    # 4) BEST / ALL 모드 분기
    results = []

    if STORE_COLLECT_MODE == "best":
        best_items = collect_best_products_on_all_products_page(driver)
        for item in best_items:
            results.append({
                "href": item["href"],
                "kind": base_kind,
                "text": item["text"],
                "brand_catalog": is_brand_catalog,
                "store": store_key,
                "store_name": store_name,
                "category_path": category_path,
                "price_before": item.get("price_before"),
                "price_after": item.get("price_after"),
            })
    else:
        # 👉 스토어 전체 페이지(1,2,3,...)를 돌면서 ALL 상품 수집
        all_items = collect_all_products_from_store(driver)
        for item in all_items:
            results.append({
                "href": item["href"],
                "kind": base_kind,
                "text": item["text"],
                "brand_catalog": is_brand_catalog,
                "store": store_key,
                "store_name": store_name,
                "category_path": category_path,
                "price_before": item.get("price_before"),
                "price_after": item.get("price_after"),
            })

    # ✅ 여기서 4단계: 수집된 링크를 상세페이지 기준으로 다시 필터링
    results = filter_records_by_detail_page(results, driver)

    return results





def create_driver():
    """크롬 드라이버 생성"""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")  # 창 최대화
        # ✅ 웨일/다른 작업하며 써도 덜 멈추게 하는 옵션들
    options.add_argument("--disable-features=CalculateNativeWinOcclusion")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def extract_brand_from_detail(driver):
    """
    상세 페이지에서 브랜드명을 추출.
    <th>브랜드</th> 바로 오른쪽 <td> 텍스트를 읽는다.
    브랜드가 없으면 빈 문자열 반환.
    """
    try:
        th = driver.find_element(By.XPATH, '//th[contains(normalize-space(.),"브랜드")]')
        td = th.find_element(By.XPATH, 'following-sibling::td[1]')
        brand = td.text.strip()
        return brand
    except Exception:
        return ""


# ===================== 새로 추가된 부분: smartstore 최종 URL 얻기 =====================
def resolve_smartstore_urls_by_click(driver, link_element, base_kind, is_brand_catalog,
                                    total_product_limit=None, record_oversize_store=None,category_path=""):
    """
    검색 결과 페이지에서 상품 <a>를 클릭해서 새 탭/창으로 연 다음,
    - smartstore / brandstore 상품으로 바로 가는 경우:
        → 해당 스토어의 '전체상품' 페이지에서 BEST 상품들을 수집
    - catalog 페이지로 가는 경우:
        → catalog 안의 smartstore/brandstore 들을 돌며 동일하게 BEST 수집
    반환: BEST 상품 record 리스트
    """
    if should_stop():
        return []
    # 🔒 0) 19금(청소년 유해상품) 상품이면 아예 클릭 안 함
    if is_adult_product_element(link_element):
        try:
            title = (link_element.get_attribute("title") or link_element.text or "").strip()
        except Exception:
            title = ""
        print(f"[SKIP] 청소년 유해상품(19금)이라 클릭하지 않음: {title}")
        return []
    
        # 🔒 0-1) 제외 몰(G마켓, 쿠팡, 11번가 등)이면 아예 클릭 안 함
    if is_skip_mall_for_link(link_element):
        # 로그는 is_skip_mall_for_link 안에서 출력됨
        return []
    
    main_handle = driver.current_window_handle
    handles_before = driver.window_handles

    # 실제 클릭으로 새 탭/창 열기
    driver.execute_script("arguments[0].click();", link_element)
    time.sleep(random.uniform(*CLICK_DELAY_RANGE))

    handles_after = driver.window_handles
    new_handles = [h for h in handles_after if h not in handles_before]
    if new_handles:
        product_handle = new_handles[0]
    else:
        # 새 탭이 안 뜨고 현재 탭이 바뀌었을 가능성 방어
        product_handle = main_handle

    driver.switch_to.window(product_handle)

        # 2) 🔍 탭 전환 직후, 캡챠 페이지인지 먼저 확인
    if not handle_captcha_if_needed(driver,client,MAX_RETRY,CLICK_DELAY_RANGE,api_key):
        # 캡챠를 해결 못 했거나 계속 남아 있으면 이 링크는 스킵
        if product_handle != main_handle:
            driver.close()
            driver.switch_to.window(main_handle)
        return []

    best_records = []

    try:
        final_url = wait_until_redirect_done(driver)


        # 1) smartstore 로 바로 간 경우 → 기존 로직 (전체상품 + BEST)
        if final_url.startswith("https://smartstore.naver.com"):
            best_records.extend(
                collect_best_from_current_store(driver, base_kind, is_brand_catalog,total_product_limit=total_product_limit,record_oversize_store=record_oversize_store,category_path=category_path)
            )

        # 2) brandstore 로 바로 간 경우 → 방금 만든 brandstore 전용 함수 사용
        elif final_url.startswith("https://brand.naver.com"):
            best_records.extend(
                collect_best_from_current_store(driver, base_kind, is_brand_catalog,total_product_limit=total_product_limit,record_oversize_store=record_oversize_store,category_path=category_path)
            )

        # 3) catalog 페이지에 도착한 경우 → 기존 로직 유지
        elif "search.shopping.naver.com/catalog" in final_url:
            best_records.extend(
                find_smartstores_in_catalog_page(
                    driver,
                    base_kind,
                    is_brand_catalog,
                    total_product_limit=total_product_limit,
                    record_oversize_store=record_oversize_store,
                    category_path=category_path
                )
            )

        # 4) 그 외 도메인은 대상 아님
        else:
            print("[INFO] smartstore/brandstore/catalog가 아닌 링크라 건너뜁니다.")

    finally:
        # 탭 정리 시, 이미 닫힌 창에 대해 close/switch 시도하다가
        # NoSuchWindowException 터지지 않도록 방어
        try:
            if product_handle != main_handle and product_handle in driver.window_handles:
                # 혹시 다른 탭에 가 있을 수도 있으니 한 번 전환 후 닫기
                driver.switch_to.window(product_handle)
                driver.close()
        except NoSuchWindowException:
            print("[WARN] product 창이 이미 닫혀 있어서 close() 생략")
        finally:
            # 메인 검색창이 아직 살아있으면 그 쪽으로 포커스 복귀
            try:
                if main_handle in driver.window_handles:
                    driver.switch_to.window(main_handle)
            except NoSuchWindowException:
                print("[WARN] main 창도 이미 닫혀 있음 (driver 세션이 끊겼을 수 있음)")

    return best_records


    return best_records



# =============================================================================


def go_to_all_products_if_exists(driver):
    """
    현재 탭이 스마트스토어 페이지라고 가정하고:
    1) '더보기' 버튼이 보이면 먼저 클릭
    2) '전체상품' 메뉴를 찾으면 클릭
    3) 전체상품 페이지로 이동한 뒤, 사용자가 엔터를 누르면
       BEST가 붙은 상품들의 상품페이지 URL 목록을 리턴
    - '전체상품'이 아예 없으면 빈 리스트 리턴
    """
    best_urls = []
    try:
        wait = WebDriverWait(driver, 5)

        # 1) '더보기' 버튼 있으면 클릭 (없으면 그냥 넘어감)
        try:
            more_btn = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, '//button[contains(normalize-space(.), "더보기")]')
                )
            )
            try:
                driver.execute_script("arguments[0].click();", more_btn)
            except Exception:
                more_btn.click()
            time.sleep(random.uniform(*CLICK_DELAY_RANGE))
        except Exception:
            # 더보기가 없는 경우 / 안 보이는 경우
            pass

        # 2) '전체상품' 링크 찾기 (data-name 또는 텍스트로 검색)
        try:
            all_link = driver.find_element(
                By.XPATH,
                '//a[@data-name="전체상품" or contains(normalize-space(.), "전체상품")]'
            )
        except Exception:
            print("[INFO] '전체상품' 메뉴가 없는 스마트스토어입니다. 그냥 넘어갑니다.")
            return []

        # 3) '전체상품' 클릭
        try:
            driver.execute_script("arguments[0].click();", all_link)
        except Exception:
            all_link.click()

        print("[INFO] '전체상품' 메뉴 클릭 완료. 페이지 확인 후 BEST 상품을 수집합니다.")
        time.sleep(random.uniform(*CLICK_DELAY_RANGE))  # 필요하면 2~5초 사이로 조절



    except Exception as e:
        print(f"[경고] 전체상품 / BEST 처리 중 오류 발생: {e}")
        return []

    return best_urls

def wait_until_redirect_done(driver, max_wait=10):
    """
    cr.shopping.naver.com/adcr 같은 중간 URL에서
    실제 목적지로 리다이렉트가 끝날 때까지 기다리고 최종 URL 반환
    """
    last_url = None
    for _ in range(max_wait * 2):  # 0.5초 * 20 = 최대 10초
        cur = driver.current_url
        # 아직 adcr / cr.shopping 단계면 계속 대기
        if "cr.shopping.naver.com" in cur:
            last_url = cur
        else:
            return cur
        time.sleep(random.uniform(*CLICK_DELAY_RANGE))
    # 타임아웃이면 현재 주소 반환
    return driver.current_url


def find_smartstores_in_catalog_page(driver, base_kind, is_brand_catalog, max_malls=50, total_product_limit=None, record_oversize_store=None,category_path=""):
    """
    카탈로그 페이지의 판매처 리스트를 ...
    """
    global BRAND_CATALOG_MODE

    catalog_handle = driver.current_window_handle
    results = []

    # 브랜드 카탈로그 모드가 'none'이면 아예 수집하지 않음
    if BRAND_CATALOG_MODE == "none":
        print("[INFO] 브랜드 카탈로그 모드가 'none'이라 카탈로그 판매처는 수집하지 않습니다.")
        return []

    # 1. 전체 행(Row) 개수를 먼저 파악
    try:
        initial_rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
        total_count = len(initial_rows)
    except Exception:
        print("[INFO] 판매처 리스트를 찾을 수 없습니다.")
        return []
    
    print(f"[INFO] 판매처 리스트 총 {total_count}개 발견. 순차적으로 확인합니다.")

    # 2. 인덱스(i)로 접근하여 하나씩 처리 (중간에 끊김 방지)
    for i in range(total_count):
        if should_stop():
            break
        # 너무 많이 수집하면 오래 걸리므로 제한 (필요시 max_malls 숫자 조절)
        if i >= max_malls:
            print(f"[INFO] 최대 방문 수({max_malls}) 도달로 중단합니다.")
            break

        try:
            # ★ 중요: 탭을 갔다오면 DOM이 불안정해지므로 매번 다시 찾습니다.
            current_rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
            if i >= len(current_rows):
                break # 리스트가 줄어들었거나 변경된 경우 중단
            
            row = current_rows[i]

            # --- 여기서부터 기존 필터링 로직 ---
            try:
                # 몰 링크 찾기
                mall_link = row.find_element(By.CSS_SELECTOR, 'a[class^="productByMall_mall__"]')
                
                # 몰 이름 확인 (이미지 alt 또는 텍스트)
                mall_name = ""
                try:
                    img = mall_link.find_element(By.TAG_NAME, "img")
                    mall_name = img.get_attribute("alt").strip()
                except Exception:
                    mall_name = mall_link.text.strip()

                # 오픈마켓 필터링 (G마켓, 옥션, 쿠팡 등 스킵)
                if any(skip_mall in mall_name for skip_mall in SKIP_MALL_ALTS):
                    # print(f"   Pass: {mall_name}") # 너무 시끄러우면 주석 처리
                    continue
                
                print(f"[{i+1}/{total_count}] 방문 시도: {mall_name}")

                # 클릭하여 새 탭 열기
                driver.execute_script("arguments[0].click();", mall_link)
                time.sleep(random.uniform(*CLICK_DELAY_RANGE))

                # 탭 전환
                handles_after = driver.window_handles
                new_handles = [h for h in handles_after if h != catalog_handle]

                if new_handles:
                    mall_handle = new_handles[-1]
                    driver.switch_to.window(mall_handle)

                    try:
                        # URL 확인
                        final_url = wait_until_redirect_done(driver)
                        
                        if final_url.startswith("https://smartstore.naver.com") or final_url.startswith("https://brand.naver.com"):
                            # print(f"   → 수집 시작 ({mall_name})")
                            store_records = collect_best_from_current_store(
                                driver,
                                base_kind,
                                is_brand_catalog,
                                total_product_limit=total_product_limit,
                                record_oversize_store=record_oversize_store,
                                category_path=category_path
                            )
                            results.extend(store_records)

                            # ⭐ 브랜드 카탈로그 모드가 'first'면, 첫 스마트스토어만 수집하고 바로 종료
                            if BRAND_CATALOG_MODE == "first" and results:
                                print("[INFO] 브랜드 카탈로그 모드 'first' → 첫 스마트스토어만 수집 후 종료")
                                return results

                        else:
                            # print(f"   → 스마트스토어 아님 ({final_url})")
                            pass

                    
                    except Exception as e:
                        print(f"[ERROR] 탭 내부 처리 중 오류: {e}")

                    finally:
                        # 탭 닫고 카탈로그 페이지로 복귀 (필수)
                        if driver.current_window_handle != catalog_handle:
                            driver.close()
                        driver.switch_to.window(catalog_handle)
                        # 복귀 후 잠시 대기 (페이지 안정화)
                        time.sleep(random.uniform(*CLICK_DELAY_RANGE))

            except Exception as inner_e:
                # 링크를 못 찾거나 하는 소소한 에러는 무시하고 다음 루프로
                continue

        except Exception as e:
            print(f"[ERROR] 판매처 순회 중 오류 발생: {e}")
            continue

    return results

def extract_category_path_from_search_card(link_el) -> str:
    """
    검색결과(첫 화면)에서 상품 a 태그(link_el)가 속한 카드의
    카테고리 breadcrumb를 'A > B > C' 형태로 추출
    """
    xpaths = [
        # 광고 카드
        './ancestor::div[contains(@class,"adProduct_item__")][1]//div[contains(@class,"depth__")]//span[contains(@class,"category__")]',
        # 일반 상품 카드
        './ancestor::div[contains(@class,"product_item__")][1]//div[contains(@class,"depth__")]//span[contains(@class,"category__")]',
        # fallback
        './ancestor::*[self::div or self::li][.//div[contains(@class,"depth__")]][1]//div[contains(@class,"depth__")]//span[contains(@class,"category__")]',
    ]

    for xp in xpaths:
        try:
            spans = link_el.find_elements(By.XPATH, xp)
            parts = [s.text.strip() for s in spans if s.text and s.text.strip()]
            if parts:
                return " > ".join(parts)
        except Exception:
            pass
    return ""

def collect_naver_links(
    driver,
    include_brand_catalog=True,
    include_ads=True,
    csv_filename_for_realtime=None,
    total_product_limit=None,
    record_oversize_store=None,
):


    records = []

    if should_stop():
        return records

    brand_hrefs = collect_brand_catalog_hrefs(driver)

    # 1) 광고 영역
    if include_ads:
        ad_elements = driver.find_elements(
            By.CSS_SELECTOR,
            'div[class^="adProduct_title__"] a[class^="adProduct_link__"]'
        )
        for el in ad_elements:
            if is_preorder_product_link(el):
                continue

            # ⭐ 희망일배송 제외 옵션
            if is_hope_delivery_product_link(el):
                continue       


            href = el.get_attribute("href")
            if not href or "javascript:" in href.lower():
                continue

            is_brand = is_brand_catalog_link(el, brand_hrefs)
            if is_brand and not include_brand_catalog:
                continue

            category_path = extract_category_path_from_search_card(el)
            if should_skip_by_category_path(category_path,FORBIDDEN_CATEGORY_TOKENS=FORBIDDEN_CATEGORY_TOKENS,FORBIDDEN_CATEGORY_PATHS=FORBIDDEN_CATEGORY_PATHS):
                print(f"[SKIP] 카테고리 금칙어 스킵: {category_path}")
                continue
            best_records = resolve_smartstore_urls_by_click(driver, el, base_kind="ad", is_brand_catalog=is_brand,total_product_limit=total_product_limit, record_oversize_store=record_oversize_store,category_path=category_path)
            records.extend(best_records)

            if csv_filename_for_realtime and best_records:
                append_to_csv_incremental(best_records, csv_filename_for_realtime)

    # 2) 일반 상품 영역
    product_elements = driver.find_elements(
        By.CSS_SELECTOR,
        'div[class^="product_title__"] a[class^="product_link__"]'
    )
    for el in product_elements:
        if is_preorder_product_link(el):
            continue

        # ⭐ 희망일배송은 항상 제외
        if is_hope_delivery_product_link(el):
            continue

        href = el.get_attribute("href")
        if not href or "javascript:" in href.lower():
            continue

        is_brand = is_brand_catalog_link(el, brand_hrefs)
        if is_brand and not include_brand_catalog:
            continue
        category_path = extract_category_path_from_search_card(el)
        if should_skip_by_category_path(category_path,FORBIDDEN_CATEGORY_TOKENS=FORBIDDEN_CATEGORY_TOKENS,FORBIDDEN_CATEGORY_PATHS=FORBIDDEN_CATEGORY_PATHS):
            print(f"[SKIP] 카테고리 금칙어 스킵: {category_path}")
            continue
        best_records = resolve_smartstore_urls_by_click(driver, el, base_kind="product", is_brand_catalog=is_brand,total_product_limit=total_product_limit, record_oversize_store=record_oversize_store,category_path=category_path)
        records.extend(best_records)

        if csv_filename_for_realtime and best_records:
            append_to_csv_incremental(best_records, csv_filename_for_realtime)

    unique = {}
    for r in records:
        unique[(r["href"], r["kind"])] = r
    return list(unique.values())





def is_hope_delivery_product_link(link_element):
    """
    검색 결과의 제목/이미지 <a> 요소에서
    같은 상품 카드 안에 '희망일배송' 뱃지가 있으면 True 반환 (수집에서 제외 용도)
    """
    try:
        # 이 링크가 속한 상품 카드 (일반/광고 둘 다)
        card = link_element.find_element(
            By.XPATH,
            './ancestor::div[contains(@class, "product_item__") or contains(@class, "adProduct_item__")][1]'
        )
    except Exception:
        # 카드 구조를 못 찾으면 그냥 희망일배송 아닌 걸로 처리
        return False

    try:
        # 카드 안에서 텍스트에 '희망일배송' 이 들어간 요소가 하나라도 있으면 True
        badge_elems = card.find_elements(
            By.XPATH,
            './/*[contains(normalize-space(.), "희망일배송")]'
        )
        if badge_elems:
            try:
                name = (link_element.get_attribute("title") or link_element.text or "").strip()
            except Exception:
                name = ""
            print(f"[SKIP] 희망일배송 상품이라 수집하지 않음: {name}")
            return True
    except Exception:
        pass

    return False

def collect_all_products_on_all_products_page(driver):
    """
    전체상품(All) 페이지의 '현재 페이지'에서만
    모든 상품 링크를 모아 리스트로 반환.

    페이지 이동(1,2,3...)은 하지 않고,
    오직 현재 화면에 보이는 상품만 수집합니다.
    """
    results = []
    cards = driver.find_elements(
        By.XPATH,
        '//li[.//a[contains(@href, "/products/")]]'
    )

    print(f"[STORE] 현재 전체상품 페이지에서 상품 카드 {len(cards)}개 발견 (ALL 모드, 단일 페이지)")

    for card in cards:
        if should_stop():
            break
        try:
            # 🔞 19금 필터 (BEST 수집과 동일한 기준 사용)
            try:
                card.find_element(By.CLASS_NAME, "adultBlock_teenager__iVi6S")
                try:
                    product_name = card.find_element(
                        By.XPATH,
                        './/a[contains(@href, "/products/")]'
                    ).get_attribute("title")
                except NoSuchElementException:
                    product_name = "이름을 찾을 수 없는 상품"
                print(f"[SKIP] 목록에서 19금 상품 마크 확인(ALL 모드): {product_name}")
                continue
            except NoSuchElementException:
                pass

            a = card.find_element(By.XPATH, './/a[contains(@href, "/products/")]')
            raw = a.get_attribute("href")
            if not raw:
                continue

            href = normalize_href(urljoin(driver.current_url, raw))

            # 상품명
            title = ""
            try:
                title_el = card.find_element(By.TAG_NAME, "strong")
                title = title_el.text.strip()
            except Exception:
                try:
                    img = card.find_element(By.TAG_NAME, "img")
                    title = img.get_attribute("alt").strip()
                except Exception:
                    title = "제목 없음"

            # 금칙어 필터
            if is_forbidden_name(title, FORBIDDEN_PRODUCT_KEYWORDS):
                print(f"[SKIP] 금지어 포함 상품 스킵(ALL 모드): {title}")
                continue

            # 가격 추출 + 필터
            before_price, after_price = price.extract_prices_from_card(card)
            if not pass_price_filter(before_price, after_price, PRICE_MODE, PRICE_MIN, PRICE_MAX):
                print(f"[SKIP] 가격 필터 스킵(ALL 모드): "
                      f"mode={PRICE_MODE}, min={PRICE_MIN}, max={PRICE_MAX}, "
                      f"before={before_price}, after={after_price}, title={title}")
                continue

            results.append({
                "href": href,
                "text": title,
                "price_before": before_price,
                "price_after": after_price,
            })

        except Exception as e:
            print(f"[ERROR] ALL 상품 파싱 중 오류: {e}")
            continue

    print(f"[INFO] (단일 페이지) ALL 상품 {len(results)}개 수집 완료")
    return results


def collect_all_products_from_store(driver, max_pages=50):
    """
    스마트스토어/브랜드스토어 '전체상품' 기준으로
    1페이지부터 max_pages까지 순서대로 돌면서
    모든 상품을 수집한다.
    """
    if should_stop():
        return []
    results = []
    seen = set()
    page_no = 1

    while True:
        if should_stop():
            break
        print(f"[STORE] 전체상품 페이지 {page_no} 수집 시작 (ALL 모드, 전체 순회)")

        # 스크롤 해서 lazy-load 상품 로딩
        scroll_page(driver, SCROLL_COUNT, SCROLL_DELAY_RANGE)

        # 현재 페이지의 상품들 수집
        page_items = collect_all_products_on_all_products_page(driver)

        page_items = filter_records_by_detail_page(page_items, driver)

        # 중복/기존 결과 제거하면서 누적
        for item in page_items:
            href = item.get("href")
            if not href:
                continue
            if href in seen or href in EXISTING_HREFS:
                continue
            seen.add(href)
            results.append(item)

        print(f"[INFO] 현재까지 ALL 상품 누적 수: {len(results)}")

        if page_no >= max_pages:
            print(f"[INFO] max_pages({max_pages}) 도달로 종료")
            break

        # 다음 페이지 번호 (page_no + 1) 버튼 찾기
        next_page_str = str(page_no + 1)

        try:
            # 화면 아래로 한 번 더 스크롤 (페이지네이션 보이게)
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(*SCROLL_DELAY_RANGE))
            except Exception:
                pass

            next_btns = driver.find_elements(
                By.XPATH,
                f'//a[normalize-space(text())="{next_page_str}"] | '
                f'//button[normalize-space(text())="{next_page_str}"]'
            )

            clicked = False
            for btn in next_btns:
                try:
                    if not btn.is_displayed():
                        continue
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(random.uniform(*CLICK_DELAY_RANGE))
                    clicked = True
                    page_no += 1
                    print(f"[STORE] {page_no-1} -> {page_no} 페이지 이동 성공")
                    break
                except Exception:
                    continue

            if not clicked:
                print("[INFO] 다음 페이지 버튼을 찾지 못했습니다. (마지막 페이지일 수 있음)")
                break

        except Exception as e:
            print(f"[ERROR] 다음 페이지 이동 중 오류: {e}")
            break

    print(f"[INFO] 스토어 전체상품에서 ALL 상품 최종 {len(results)}개 수집 완료")
    return results





def is_excluded_by_detail_filters(driver):
    """
    현재 탭이 상품 상세 페이지라고 가정하고,
    상단 안내 박스의 '맞춤제작 상품 / 해외직배송 상품 / 예약구매 상품'
    뱃지 기준으로만 필터링한다.
    (리뷰/문의 영역 텍스트는 아예 신경 안 씀)
    """
    if not (EXCLUDE_CUSTOM or EXCLUDE_OVERSEAS or EXCLUDE_PREORDER_DETAIL):
        # 아무 필터도 선택 안 하면 검사 자체를 안 함
        return False

    # 1) 맞춤제작 상품 뱃지
    if EXCLUDE_CUSTOM:
        if _has_notice_badge(
            driver,
            texts=["맞춤제작 상품", "맞춤 제작 상품"],
            classes=["ZQxvUGdfvP"],  # 네가 캡쳐한 strong 클래스
        ):
            print("[SKIP] 상세 상단 뱃지 기준: 맞춤제작 상품이라 제외합니다.")
            return True

    # 2) 해외직배송 상품 뱃지
    if EXCLUDE_OVERSEAS:
        if _has_notice_badge(
            driver,
            texts=["해외직배송 상품", "해외 직배송 상품"],
            classes=["ntgWQwXmJb"],  # 네가 캡쳐한 strong 클래스
        ):
            print("[SKIP] 상세 상단 뱃지 기준: 해외직배송 상품이라 제외합니다.")
            return True

    # 3) 예약구매 상품 뱃지
    if EXCLUDE_PREORDER_DETAIL:
        # 예약구매는 정확한 class 이름이 없어도, 텍스트로는 거의 고정이라 가정
        if _has_notice_badge(
            driver,
            texts=["예약구매 상품", "예약 구매 상품", "예약구매"],
            classes=[],
        ):
            print("[SKIP] 상세 상단 뱃지 기준: 예약구매 상품이라 제외합니다.")
            return True

        # + 영어 pre-order 문구도 상단 안내에 들어가는 경우 대비 (리뷰 안 봄)
        try:
            html_top = driver.page_source[:30000].lower()
            if "pre-order" in html_top and "order" in html_top:
                print("[SKIP] pre-order 문구 감지: 예약구매 상품으로 간주합니다.")
                return True
        except Exception:
            pass

    return False




from selenium.webdriver.common.by import By  # 이미 있으면 생략

def _has_notice_badge(driver, texts, classes=None):
    """
    상세페이지 상단의 안내 박스(맞춤제작/해외직배송/예약구매 등)를
    strong/span 요소 기준으로 판정한다.
    - texts: ['맞춤제작 상품', '맞춤 제작 상품'] 이런 후보들
    - classes: ['ZQxvUGdfvP'] 같이 class 이름으로도 한 번 더 체크
    """
    # 1) 클래스 이름으로 먼저 체크 (정확도↑)
    if classes:
        for cls in classes:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, f"strong.{cls}, span.{cls}")
                for el in els:
                    t = (el.text or "").strip()
                    if any(key in t for key in texts):
                        return True
            except Exception:
                pass

    # 2) strong / span 텍스트 기준 (클래스가 바뀌었을 때 대비)
    joined = " or ".join([f"contains(normalize-space(), '{t}')" for t in texts])
    xpath = f"//strong[{joined}] | //span[{joined}]"

    try:
        els = driver.find_elements(By.XPATH, xpath)
        if els:
            return True
    except Exception:
        pass

    return False



def filter_records_by_detail_page(records, driver):
    """
    전체상품/베스트에서 수집한 records 리스트를 받아서
    각 상품의 상세 페이지를 실제로 열어본 뒤,
    EXCLUDE_* 옵션에 따라 맞춤제작 / 해외직배송 / 예약구매 / (희망일배송) 등을 체크한다.

    - records: [{ "href": ..., "text": ..., ...}, ...]
    - driver: 현재 검색/스토어 페이지를 열고 있는 webdriver
    """
    # 상세 필터 옵션도 없고, 브랜드 금칙어도 없으면 상세페이지 안 들어감
    if not (EXCLUDE_CUSTOM or EXCLUDE_OVERSEAS or EXCLUDE_PREORDER_DETAIL or FORBIDDEN_BRAND_KEYWORDS):
        return records



    filtered = []
    try:
        main_handle = driver.current_window_handle
    except Exception:
        # 탭 정보 못 가져오면 그냥 필터링 생략
        return records

    for rec in records:
        if should_stop():
            break
        href = rec.get("href")
        if not href:
            continue

        try:
            handles_before = driver.window_handles

            # 새 탭으로 상품 상세 페이지 열기
            driver.execute_script("window.open(arguments[0], '_blank');", href)
            time.sleep(random.uniform(*CLICK_DELAY_RANGE))

            handles_after = driver.window_handles
            new_handles = [h for h in handles_after if h not in handles_before]
            if not new_handles:
                # 새 탭이 안 열렸으면 스킵
                continue

            detail_handle = new_handles[0]
            driver.switch_to.window(detail_handle)


            # --- 상품 존재 여부 먼저 확인 (네이버 버그 대응) ---
            if is_product_not_exist(driver):
                print("[PENDING] 상품이 존재하지 않습니다 → 보류 목록에 추가:", href)
                PENDING_RECHECK.append(rec)

                # 보류 누적 개수가 많으면 잠시 쉬기
                if len(PENDING_RECHECK) >= 5 and (len(PENDING_RECHECK) % 5 == 0):
                    wait_sec = 60
                    print(f"[COOLDOWN] '상품이 존재하지 않습니다' 누적 {len(PENDING_RECHECK)}개 → {wait_sec}초 대기")
                    gui_log(f"⚠️ 네이버 상품 오류 빈번 → {wait_sec}초 대기합니다...")
                    for i in range(wait_sec):
                        time.sleep(1)

                
                # 탭 닫고 메인으로 복귀 후 다음 상품 진행
                try:
                    if detail_handle in driver.window_handles:
                        driver.close()
                except:
                    pass
                driver.switch_to.window(main_handle)
                continue




            # 캡챠 대응
            if not handle_captcha_if_needed(driver, client, MAX_RETRY, CLICK_DELAY_RANGE, api_key):
                # 캡챠를 해결 못하면 이 상품은 그냥 스킵
                try:
                    if detail_handle in driver.window_handles:
                        driver.close()
                except Exception:
                    pass
                driver.switch_to.window(main_handle)
                continue

            # ✅ 여기서 상세 HTML 기준으로 필터링
            if is_excluded_by_detail_filters(driver):
                # 맞춤제작 / 예약구매 / 해외직배송 등 옵션에 따라 제외
                # (is_excluded_by_detail_filters 내부에서 EXCLUDE_* 보고 판단)
                continue

            # ✅ 브랜드 금칙어 필터
            if FORBIDDEN_BRAND_KEYWORDS:
                brand = extract_brand_from_detail(driver)
                if brand:
                    blocked = False
                    for kw in FORBIDDEN_BRAND_KEYWORDS:
                        if kw and kw in brand:
                            print(f"[SKIP] 브랜드 금칙어({kw}) 포함 → 제외: {brand} | href={href}")
                            blocked = True
                            break
                    if blocked:
                        try:
                            if detail_handle in driver.window_handles:
                                driver.close()
                        except Exception:
                            pass
                        driver.switch_to.window(main_handle)
                        continue

            # 통과한 상품만 남김
            filtered.append(rec)

        except NoSuchWindowException:
            print("[WARN] 상세 탭이 예기치 않게 닫혔습니다.")
        except Exception as e:
            print(f"[ERROR] 상세 페이지 필터링 중 오류: {e}")
        finally:
            # 상세 탭 정리 + 메인 탭 복귀
            try:
                cur = driver.current_window_handle
            except Exception:
                cur = None

            try:
                if cur and cur != main_handle and cur in driver.window_handles:
                    driver.close()
            except Exception:
                pass

            try:
                if main_handle in driver.window_handles:
                    driver.switch_to.window(main_handle)
            except Exception:
                pass

    print(f"[INFO] 상세페이지 기준 필터링 완료: {len(records)}개 → {len(filtered)}개")
    return filtered







def open_category_selector():
    global driver,api_key,client

    # driver 없거나 죽었으면 새로 생성
    if driver is None:
        driver = create_driver()
    else:
        try:
            _ = driver.current_url
        except WebDriverException:
            driver = create_driver()

    driver.get(START_URL)
    gui_log("[INFO] 네이버 쇼핑 카테고리 페이지를 열었습니다.")


    # 혹시 캡챠 뜨면 처리
    api_key=key_entry.get().strip() 
    try:
        handle_captcha_if_needed(driver,client,MAX_RETRY,CLICK_DELAY_RANGE,api_key=api_key)
    except Exception as e:
        gui_log(f"[WARN] 캡챠 처리 중 오류: {e}")

    messagebox.showinfo(
        "카테고리 선택",
        "크롬 창에서 원하는 카테고리/필터를 모두 고른 뒤,\n"
        "[수집하기] 버튼을 눌러주세요."
    )

def run_crawler(start_page, 
                end_page, 
                include_brand_catalog, 
                product_forbidden_path=None,
                seller_forbidden_path=None,
                owner_forbidden_path=None,
                category_forbidden_path=None,
                brand_forbidden_path=None,
                include_ads=True,
                api_key=None,
                output_name="",
                total_product_limit=None,
                price_mode="none",
                price_min=None,
                price_max=None,
                exclude_custom=False,
                exclude_overseas=False,
                exclude_preorder_detail=False,
                store_collect_mode="best",
                ):



    """
    GUI에서 받은 설정값으로 크롤링 실행.
    - driver: 이미 open_category_selector 에서 열린 상태라고 가정.
    """

    global FORBIDDEN_PRODUCT_KEYWORDS, FORBIDDEN_SELLER_KEYWORDS, FORBIDDEN_OWNER_KEYWORDS, FORBIDDEN_BRAND_KEYWORDS
    global VISITED_STORE_KEYS, FORBIDDEN_CATEGORY_KEYWORDS
    global FORBIDDEN_CATEGORY_TOKENS, FORBIDDEN_CATEGORY_PATHS
    global BRAND_CATALOG_MODE

    global EXCLUDE_CUSTOM, EXCLUDE_OVERSEAS, EXCLUDE_PREORDER_DETAIL

    EXCLUDE_CUSTOM = exclude_custom
    EXCLUDE_OVERSEAS = exclude_overseas
    EXCLUDE_PREORDER_DETAIL = exclude_preorder_detail

    global STORE_COLLECT_MODE
    STORE_COLLECT_MODE = store_collect_mode


    if driver is None:
        gui_log("[ERROR] driver 가 없습니다. 먼저 [카테고리 필터 선택]을 눌러주세요.")
        return

        # 🔍 driver 세션은 있는데 창이 닫혀 있는 경우 방어
    try:
        if not driver.window_handles:
            gui_log("[ERROR] 크롬 창이 모두 닫혀 있습니다. [카테고리 필터 선택]으로 다시 열어주세요.")
            return
    except (WebDriverException, NoSuchWindowException):
        gui_log("[ERROR] 크롬 창에 접근할 수 없습니다. [카테고리 필터 선택]으로 다시 열어주세요.")
        return



    # ✅ 수집 시작할 때마다 기준 카테고리 URL로 복귀 (스마트스토어/상세탭에 있어도 정상화)
    try:
        if CATEGORY_URL:
            driver.get(CATEGORY_URL)
            time.sleep(random.uniform(*CLICK_DELAY_RANGE))
    except Exception as e:
        gui_log(f"[WARN] 카테고리 URL 복귀 실패: {e}")

    # 금칙어 로딩
    # 상품명
    FORBIDDEN_PRODUCT_KEYWORDS = load_keywords_set_from_path(product_forbidden_path, "상품명 금지어")

    # 상호명 / 대표자
    FORBIDDEN_SELLER_KEYWORDS = load_keywords_set_from_path(seller_forbidden_path, "상호명 금지어")
    FORBIDDEN_OWNER_KEYWORDS  = load_keywords_set_from_path(owner_forbidden_path,  "대표자 금지어")

    # 카테고리명
    FORBIDDEN_CATEGORY_KEYWORDS = load_keywords_set_from_path(category_forbidden_path, "카테고리명 금지어")
    FORBIDDEN_CATEGORY_TOKENS, FORBIDDEN_CATEGORY_PATHS = prepare_forbidden_category_sets(FORBIDDEN_CATEGORY_KEYWORDS)

    # 브랜드명
    FORBIDDEN_BRAND_KEYWORDS = load_keywords_set_from_path(brand_forbidden_path, "브랜드 금지어")


    

    print("[DEBUG] category tokens:", FORBIDDEN_CATEGORY_TOKENS)
    print("[DEBUG] category paths :", FORBIDDEN_CATEGORY_PATHS)

    VISITED_STORE_KEYS = set()


    # --- 브랜드 카탈로그 모드 설정 (all / first / none) ---
    # include_brand_catalog 인자는 이제 모드 문자열로 들어옴
    if include_brand_catalog in ("all", "first", "none"):
        BRAND_CATALOG_MODE = include_brand_catalog
    else:
        BRAND_CATALOG_MODE = "all"

    # 검색결과에서 브랜드 카탈로그를 클릭할지 여부 (none이면 아예 클릭 안 함)
    include_brand_catalog_bool = (BRAND_CATALOG_MODE != "none")

    prefix = sanitize_filename(output_name) or "naver_links"

    # --- 전체상품개수 저장용 파일 세팅 ---
    oversize_csv = None
    oversize_xlsx = None
    oversize_sheet = None

    if total_product_limit is not None:
        oversize_sheet = f"전체상품개수 {total_product_limit}개 이상 스토어"
        oversize_csv  = f"{prefix}.전체상품개수_{total_product_limit}개_이상_스토어.csv"
        oversize_xlsx = f"{prefix}.전체상품개수_{total_product_limit}개_이상_스토어.xlsx"

    def record_oversize_store(rec: dict):
        if not oversize_csv:
            return
        append_to_csv_incremental([rec], oversize_csv)
        # gui_log(f"[SKIP-LIMIT] 전체상품 {rec.get('total_products')}개 ≥ 기준({total_product_limit}) → {rec.get('store_name')}")

    # 처음에는 0개로 시작 (파일명은 페이지 돌면서 계속 갱신됨)
    excel_filename = build_output_filename(prefix, start_page, end_page, 0, "xlsx")
    csv_filename   = build_output_filename(prefix, start_page, end_page, 0, "csv")
    all_records = []


    handle_captcha_if_needed(driver,client,MAX_RETRY,CLICK_DELAY_RANGE,api_key=api_key)

    gui_log(f">>> {start_page} 페이지부터 {end_page} 페이지까지 수집 시작")

    for page in range(start_page, end_page):
        if STOP_REQUESTED:
            gui_log(f"[STOP] {page-1} 페이지부터는 중단합니다.")
            break

        gui_log("=" * 60)
        gui_log(f"[{page} 페이지] 수집 시작")

        if page == start_page:
            if page == 1:
                gui_log("1페이지부터 시작합니다.")
            else:
                gui_log(f"1페이지에서 {page}페이지로 점프합니다.")
                go_to_page_smart_from_first(driver, page,CLICK_DELAY_RANGE)
        else:
            go_to_next_page(driver, CLICK_DELAY_RANGE)

        scroll_page(driver, SCROLL_COUNT, SCROLL_DELAY_RANGE)

        new_links = collect_naver_links(
        driver,
        include_brand_catalog_bool,
        include_ads=include_ads,
        csv_filename_for_realtime=csv_filename,
        total_product_limit=total_product_limit,
        record_oversize_store=record_oversize_store,
    )


        gui_log(f"[{page} 페이지] 새로 수집된 raw 링크 개수: {len(new_links)}")

        merged = {}
        for r in all_records + new_links:
            key = (r["href"], r["kind"])
            merged[key] = r
        all_records = list(merged.values())

        save_to_excel(all_records, excel_filename)
        save_to_csv(all_records, csv_filename)
        gui_log(f"[{page} 페이지]까지 누적 링크 개수: {len(all_records)}")

        # ✅ 파일명에 "현재 저장된 링크 수" 반영해서 rename
        new_count = len(all_records)
        new_excel = build_output_filename(prefix, start_page, end_page, new_count, "xlsx")
        new_csv   = build_output_filename(prefix, start_page, end_page, new_count, "csv")

        try:
            if new_excel != excel_filename and os.path.exists(excel_filename):
                os.replace(excel_filename, new_excel)
                excel_filename = new_excel

            if new_csv != csv_filename and os.path.exists(csv_filename):
                os.replace(csv_filename, new_csv)
                csv_filename = new_csv

        except Exception as e:
            gui_log(f"[WARN] 파일명 변경(rename) 실패: {e}")
        # 🔹 이 페이지까지 정상적으로 끝났으니, 재시작 정보 갱신
        try:
            global LAST_FINISHED_PAGE
            LAST_FINISHED_PAGE = page
            if ORIG_START_PAGE is not None and ORIG_END_PAGE is not None:
                save_resume_state(ORIG_START_PAGE, ORIG_END_PAGE, page)
        except Exception as e:
            gui_log(f"[WARN] 재시작 정보 저장 실패: {e}")


    gui_log("=== 수집 종료 ===")
    # ======================================================
    # 🔥 보류된 상품 재확인 로직 시작
    # ======================================================
    global PENDING_RECHECK, FAIL_RECORDS
    if PENDING_RECHECK:
        gui_log(f"[RECHECK] 보류된 상품 {len(PENDING_RECHECK)}개 재확인 시작")

        for rec in PENDING_RECHECK:
            href = rec.get("href")
            if not href:
                continue

            try:
                # 새 탭 열기
                handles_before = driver.window_handles
                driver.execute_script("window.open(arguments[0], '_blank');", href)
                time.sleep(random.uniform(*CLICK_DELAY_RANGE))

                handles_after = driver.window_handles
                new_handles = [h for h in handles_after if h not in handles_before]

                if not new_handles:
                    print("[FAIL] 새 탭 생성 실패:", href)
                    FAIL_RECORDS.append(rec)
                    continue

                detail_handle = new_handles[0]
                driver.switch_to.window(detail_handle)

                # 캡챠 자동 처리
                if not handle_captcha_if_needed(driver, client, MAX_RETRY, CLICK_DELAY_RANGE, api_key):
                    print("[FAIL] 캡챠 처리 실패:", href)
                    FAIL_RECORDS.append(rec)
                    continue

                # 다시 상품 존재 여부 확인
                if is_product_not_exist(driver):
                    print("[FAIL] 2회 확인 실패 - 상품 존재하지 않음:", href)
                    FAIL_RECORDS.append(rec)
                else:
                    print("[RECOVER] 상품 정상 표시됨 → 기존 상세 필터 적용:", href)

                    # 상세 필터 기준으로 재검사
                    if not is_excluded_by_detail_filters(driver):
                        all_records.append(rec)
                        print("[RECOVER] 최종 포함됨:", href)
                    else:
                        print("[RECOVER] 상세필터에서 제외:", href)

            except Exception as e:
                print("[ERROR] 보류 재확인 중 오류:", href, e)
                FAIL_RECORDS.append(rec)

            finally:
                # 탭 닫고 메인으로 복귀
                try:
                    driver.close()
                except:
                    pass

                try:
                    driver.switch_to.window(handles_before[0])
                except:
                    pass

        gui_log(f"[RECHECK DONE] 복구된 상품: {len(PENDING_RECHECK) - len(FAIL_RECORDS)}개")
        gui_log(f"[RECHECK DONE] 실패한 상품: {len(FAIL_RECORDS)}개")

    # ======================================================
    # 🔥 FAIL LIST 저장
    # ======================================================
    if FAIL_RECORDS:
        fail_csv = f"{prefix}_fail.csv"
        save_to_csv(FAIL_RECORDS, fail_csv)
        gui_log(f"[FAIL SAVE] 최종 실패 상품 {len(FAIL_RECORDS)}개 저장 → {fail_csv}")

    # ======================================================
    # 🔥 전체상품 초과 스토어 저장 (기존 기능 유지)
    # ======================================================
    if oversize_csv and oversize_xlsx and os.path.exists(oversize_csv):
        from crawling.output_save.output_save import csv_to_excel
        csv_to_excel(oversize_csv, oversize_xlsx, sheet_name=oversize_sheet)
        gui_log(f"[DONE] '{oversize_sheet}' 엑셀 저장 완료: {oversize_xlsx}")




def copy_log_to_clipboard():
    try:
        log_text_content = log_text.get("1.0", "end").strip()
        root.clipboard_clear()
        root.clipboard_append(log_text_content)
        gui_log("[INFO] 로그 내용을 클립보드에 복사했습니다.")
    except Exception as e:
        gui_log(f"[ERROR] 로그 복사 중 오류: {e}")


################################################################
# gui
################################################################
root = tk.Tk()

root.title("네이버 베스트 상품 링크 수집 프로그램")

forbidden_path_var = tk.StringVar(value="")

# ==========================
#  스크롤 가능한 메인 프레임
# ==========================
container = ttk.Frame(root)
container.pack(fill="both", expand=True)

# 캔버스 + 스크롤바
canvas = tk.Canvas(container)
canvas.pack(side="left", fill="both", expand=True)

scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")

canvas.configure(yscrollcommand=scrollbar.set)

# 실제 위젯들을 올릴 프레임
main_frame = ttk.Frame(canvas, padding=10)

# ✅ 2컬럼 컨테이너
cols = ttk.Frame(main_frame)
cols.pack(fill="both", expand=True)

left_col = ttk.Frame(cols)
right_col = ttk.Frame(cols)

left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
right_col.pack(side="left", fill="both", expand=True)


canvas.create_window((0, 0), window=main_frame, anchor="nw")

# 내용 크기에 맞춰 스크롤 영역 갱신
def _on_main_frame_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

main_frame.bind("<Configure>", _on_main_frame_configure)


# 1. 사용법 설명
usage_frame = ttk.LabelFrame(left_col, text="사용법")
usage_frame.pack(fill="x", pady=(0, 10))

usage_text = (
    "1. [카테고리 필터 선택] 버튼을 눌러서 크롬에서 원하는 카테고리를 직접 고릅니다.\n"
    "2. 수집할 페이지 번호를 '몇 페이지부터 ~ 몇 페이지까지' 숫자로 적습니다.\n"
    "3. 포함 여부와 시간(클릭 속도)을 정합니다.\n"
    "4. 금칙어 파일을 선택합니다.\n"
    "5. [수집하기] 버튼을 누르면 프로그램이 자동으로 페이지를 모읍니다."
)
usage_label = ttk.Label(usage_frame, text=usage_text, justify="left")
usage_label.pack(anchor="w")

# --- ⭐ 7. API Key 설정 섹션 추가 ---
api_key_frame = ttk.LabelFrame(left_col, text="API Key 입력")
api_key_frame.pack(fill="x", pady=(0, 10))

# Key 입력
key_label = ttk.Label(api_key_frame, text="Key 입력:")
key_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

key_entry = ttk.Entry(api_key_frame, width=50)
key_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

# 2. 카테고리 필터 선택
category_frame = ttk.LabelFrame(left_col, text="카테고리 필터 직접 선택")
category_frame.pack(fill="x", pady=(0, 10))


exclude_custom_var = tk.BooleanVar(value=False)          # 맞춤제작 상품 제외
exclude_overseas_var = tk.BooleanVar(value=False)        # 해외직배송 상품 제외
exclude_preorder_detail_var = tk.BooleanVar(value=False) # 예약구매 상품 제외


def select_forbidden_file():
    global forbidden_path_var
    path = filedialog.askopenfilename(
        title="금칙어 텍스트 파일 선택",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if path:
        forbidden_path_var.set(path)
        path_label.config(text=path)
        gui_log(f"[INFO] 상품 금칙어 파일 선택: {path}")
    else:
        forbidden_path_var.set("")
        path_label.config(text="")
        gui_log("[INFO] 상품 금칙어 파일 선택 취소")

category_button = ttk.Button(
    category_frame,
    text="카테고리 필터 선택 (크롬 열기)",
    command=open_category_selector
)
category_button.pack(anchor="w", pady=5)

# --- 저장 이름 입력 ---
name_frame = ttk.LabelFrame(left_col, text="저장 파일 이름")
name_frame.pack(fill="x", pady=(0, 10))

output_name_var = tk.StringVar(value="")  
ttk.Label(name_frame, text="이름:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
ttk.Entry(name_frame, textvariable=output_name_var, width=30).grid(row=0, column=1, padx=5, pady=5, sticky="w")

# 3. 수집할 페이지 범위
page_frame = ttk.LabelFrame(left_col, text="수집할 페이지 선택")
page_frame.pack(fill="x", pady=(0, 10))

start_page_var = tk.IntVar(value=1)
end_page_var = tk.IntVar(value=5)

start_label = ttk.Label(page_frame, text="시작 페이지:")
start_label.grid(row=0, column=0, padx=(5, 2), pady=5, sticky="e")
start_entry = ttk.Entry(page_frame, textvariable=start_page_var, width=10)
start_entry.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="w")
start_suffix = ttk.Label(page_frame, text="페이지부터")
start_suffix.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")

end_label = ttk.Label(page_frame, text="/  끝 페이지:")
end_label.grid(row=0, column=3, padx=(5, 2), pady=5, sticky="e")
end_entry = ttk.Entry(page_frame, textvariable=end_page_var, width=10)
end_entry.grid(row=0, column=4, padx=(0, 10), pady=5, sticky="w")
end_suffix = ttk.Label(page_frame, text="페이지까지")
end_suffix.grid(row=0, column=5, padx=(0, 5), pady=5, sticky="w")

total_product_limit = tk.IntVar(value=0)  # 0이면 기능 OFF
limit_frame = ttk.LabelFrame(left_col, text="전체상품 개수 제한")
limit_frame.pack(fill="x", pady=(0, 10))

ttk.Label(limit_frame, text="기준 개수:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
ttk.Entry(limit_frame, textvariable=total_product_limit, width=10).grid(row=0, column=1, padx=5, pady=5, sticky="w")
ttk.Label(limit_frame, text="개 이상이면 제외/별도저장").grid(row=0, column=2, padx=5, pady=5, sticky="w")


# 4. 브랜드 카탈로그 스마트스토어 수집 옵션
link_frame = ttk.LabelFrame(left_col, text="브랜드 카탈로그 스마트스토어 수집 옵션")
link_frame.pack(fill="x", pady=(0, 10))

# all / first / none 중 하나 선택
link_option_var = tk.StringVar(value="all")  # 기본값: 모두 수집

# ① 카탈로그 판매처의 스마트스토어 모두 수집
rb_bc_all = ttk.Radiobutton(
    link_frame,
    text="브랜드 카탈로그 스마트스토어 모두 수집",
    variable=link_option_var,
    value="all"
)
rb_bc_all.pack(anchor="w", padx=5, pady=2)

# ② 카탈로그 판매처 중 첫 번째 스마트스토어만 수집
rb_bc_first = ttk.Radiobutton(
    link_frame,
    text="브랜드 카탈로그에서 첫 번째 스마트스토어만 수집",
    variable=link_option_var,
    value="first"
)
rb_bc_first.pack(anchor="w", padx=5, pady=2)

# ③ 브랜드 카탈로그는 아예 수집하지 않음
rb_bc_none = ttk.Radiobutton(
    link_frame,
    text="브랜드 카탈로그 수집 안 함",
    variable=link_option_var,
    value="none"
)
rb_bc_none.pack(anchor="w", padx=5, pady=2)



# 상품 상세 필터 옵션
detail_filter_frame = ttk.LabelFrame(left_col, text="상품 상세 필터 (중복 선택 가능)")
detail_filter_frame.pack(fill="x", pady=(0, 10))

cb_custom = ttk.Checkbutton(
    detail_filter_frame,
    text="맞춤제작 상품 제외",
    variable=exclude_custom_var
)
cb_custom.pack(anchor="w", padx=5, pady=2)

cb_overseas = ttk.Checkbutton(
    detail_filter_frame,
    text="해외직배송 상품 제외",
    variable=exclude_overseas_var
)
cb_overseas.pack(anchor="w", padx=5, pady=2)

cb_preorder_detail = ttk.Checkbutton(
    detail_filter_frame,
    text="예약구매 상품 제외",
    variable=exclude_preorder_detail_var
)
cb_preorder_detail.pack(anchor="w", padx=5, pady=2)




# 4-1. 광고 링크 옵션 (라디오 버튼)
ad_frame = ttk.LabelFrame(left_col, text="광고 링크 옵션")
ad_frame.pack(fill="x", pady=(0, 10))

ad_option_var = tk.StringVar(value="include")  # 기본값: 포함

ad_include_radio = ttk.Radiobutton(ad_frame, text="광고 포함",variable=ad_option_var, value="include")
ad_include_radio.pack(side="left", padx=5, pady=2)

ad_exclude_radio = ttk.Radiobutton(ad_frame, text="광고 불포함",variable=ad_option_var, value="exclude")
ad_exclude_radio.pack(side="left", padx=5, pady=2)


# 스마트스토어 수집 모드 (BEST / ALL)
store_collect_frame = ttk.LabelFrame(left_col, text="스마트스토어 수집 모드")
store_collect_frame.pack(fill="x", pady=(0, 10))

store_collect_var = tk.StringVar(value="best")  # 기본값 BEST 수집

rb_best = ttk.Radiobutton(
    store_collect_frame,
    text="BEST 상품만 수집",
    variable=store_collect_var,
    value="best"
)
rb_best.pack(anchor="w", padx=5, pady=2)

rb_all = ttk.Radiobutton(
    store_collect_frame,
    text="전체상품(All) 모두 수집",
    variable=store_collect_var,
    value="all"
)
rb_all.pack(anchor="w", padx=5, pady=2)




# 5. 시간 
time_frame = ttk.LabelFrame(left_col, text="클릭 시간 설정")
time_frame.pack(fill="x", pady=(0, 10))

min_click_sec_var = tk.IntVar(value=2)
max_click_sec_var = tk.IntVar(value=5)

# 클릭 간격
click_label1 = ttk.Label(time_frame, text="클릭 간격:")
click_label1.grid(row=0, column=0, padx=(5, 2), pady=5, sticky="e")

min_click_entry = ttk.Entry(time_frame, textvariable=min_click_sec_var, width=5)
min_click_entry.grid(row=0, column=1, padx=(0, 2), pady=5, sticky="w")

click_mid_label = ttk.Label(time_frame, text="초 와")
click_mid_label.grid(row=0, column=2, padx=(0, 2), pady=5, sticky="w")

max_click_entry = ttk.Entry(time_frame, textvariable=max_click_sec_var, width=5)
max_click_entry.grid(row=0, column=3, padx=(0, 2), pady=5, sticky="w")

click_suffix = ttk.Label(time_frame, text="초 사이에 한 번 클릭")
click_suffix.grid(row=0, column=4, padx=(0, 5), pady=5, sticky="w")

def select_keyword_file(var, label, kind):
    path = filedialog.askopenfilename(
        title=f"{kind} 파일 선택",
        filetypes=[("텍스트 파일", "*.txt")]
    )
    if not path:
        return

    var.set(path)
    label.config(text=path)
    print(f"[INFO] {kind} 파일 선택:", path)

    # 🔥 금칙어 파일 내용도 바로 출력
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # 세미콜론 기준 split
        keywords = [kw.strip() for kw in content.split(";") if kw.strip()]

        print(f"[INFO] {kind} 금칙어 목록 ({len(keywords)}개): {keywords}")

    except Exception as e:
        print(f"[ERROR] {kind} 금칙어 파일을 읽을 수 없음:", e)


price_frame = ttk.LabelFrame(right_col, text="가격 필터 (선택)")
price_frame.pack(fill="x", pady=(0, 10))

price_filter_var = tk.StringVar(value="none")  # none | before | after
price_min_var = tk.StringVar(value="")
price_max_var = tk.StringVar(value="")

ttk.Radiobutton(price_frame, text="미사용", variable=price_filter_var, value="none").grid(row=0, column=0, padx=5, pady=5, sticky="w")
ttk.Radiobutton(price_frame, text="할인 전", variable=price_filter_var, value="before").grid(row=0, column=1, padx=5, pady=5, sticky="w")
ttk.Radiobutton(price_frame, text="할인 후", variable=price_filter_var, value="after").grid(row=0, column=2, padx=5, pady=5, sticky="w")

ttk.Label(price_frame, text="가격 범위:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
ttk.Entry(price_frame, textvariable=price_min_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky="w")
ttk.Label(price_frame, text="~").grid(row=1, column=2, padx=5, pady=5)
ttk.Entry(price_frame, textvariable=price_max_var, width=10).grid(row=1, column=3, padx=5, pady=5, sticky="w")
ttk.Label(price_frame, text="(원)").grid(row=1, column=4, padx=5, pady=5, sticky="w")

existing_frame = ttk.LabelFrame(right_col, text="기존 결과 엑셀 업로드 (중복 제외용, 최대 100개)")
existing_frame.pack(fill="x", pady=(0, 10))

existing_result_paths_var = tk.Variable(value=())

existing_count_label = ttk.Label(existing_frame, text="선택된 파일: 0개")
existing_count_label.pack(anchor="w", padx=5, pady=(5, 0))

existing_preview = tk.Text(existing_frame, height=4, wrap="word")
existing_preview.pack(fill="x", padx=5, pady=5)

def select_existing_result_files():
    paths = filedialog.askopenfilenames(
        title="기존 결과 엑셀 선택 (A열이 href)",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )
    if not paths:
        existing_result_paths_var.set(())
        existing_count_label.config(text="선택된 파일: 0개")
        existing_preview.delete("1.0", "end")
        gui_log("[INFO] 기존 결과 엑셀 선택 취소")
        return

    paths = list(paths)
    if len(paths) > 100:
        messagebox.showwarning("파일 개수 제한", "최대 100개까지만 넣을 수 있어요. 앞에서 100개만 사용합니다.")
        paths = paths[:100]

    existing_result_paths_var.set(tuple(paths))
    existing_count_label.config(text=f"선택된 파일: {len(paths)}개")

    existing_preview.delete("1.0", "end")
    show_list = paths[:10]
    existing_preview.insert("end", "\n".join(show_list))
    if len(paths) > 10:
        existing_preview.insert("end", f"\n... 외 {len(paths)-10}개")

    gui_log(f"[INFO] 기존 결과 엑셀 {len(paths)}개 선택 완료")

ttk.Button(
    existing_frame,
    text="기존 결과 엑셀 여러 개 선택",
    command=select_existing_result_files
).pack(anchor="w", padx=5, pady=(0, 5))

# 6. 금칙어 파일 업로드 섹션
forbidden_frame = ttk.LabelFrame(right_col, text="상품 금칙어 파일 선택 ( ; 기준으로 분류합니다. 선택 사항)")
forbidden_frame.pack(fill="x", pady=(0, 10))

command=select_forbidden_file 

file_button = ttk.Button(
    forbidden_frame,
    text="상품 금칙어 파일 선택 (*.txt)",
    command=select_forbidden_file 
)
file_button.pack(anchor="w", padx=5, pady=5)

path_label = ttk.Label(
    forbidden_frame,

    wraplength=400,
    foreground="blue"
)
path_label.pack(anchor="w", padx=5, pady=(0, 5))

seller_forbidden_path_var = tk.StringVar(value="")
seller_forbidden_frame = ttk.LabelFrame(right_col, text="상호명 금칙어 파일 선택 ( ; 기준으로 분류합니다. 선택 사항)")
seller_forbidden_frame.pack(fill="x", pady=(0, 10))
ttk.Button(
    seller_forbidden_frame,
    text="상호명 금칙어 파일 선택 (*.txt)",
    command=lambda: select_keyword_file(seller_forbidden_path_var, seller_path_label, "상호명 금칙어")
).pack(anchor="w", padx=5, pady=5)
seller_path_label = ttk.Label(seller_forbidden_frame, wraplength=400, foreground="blue")
seller_path_label.pack(anchor="w", padx=5, pady=(0, 5))

owner_forbidden_path_var  = tk.StringVar(value="")
owner_forbidden_frame = ttk.LabelFrame(right_col, text="대표자 금칙어 파일 선택 ( ; 기준으로 분류합니다. 선택 사항)")
owner_forbidden_frame.pack(fill="x", pady=(0, 10))
ttk.Button(
    owner_forbidden_frame,
    text="대표자 금칙어 파일 선택 (*.txt)",
    command=lambda: select_keyword_file(owner_forbidden_path_var, owner_path_label, "대표자 금칙어")
).pack(anchor="w", padx=5, pady=5)
owner_path_label = ttk.Label(owner_forbidden_frame, wraplength=400, foreground="blue")
owner_path_label.pack(anchor="w", padx=5, pady=(0, 5))

# 카테고리 금칙어 
category_forbidden_path_var = tk.StringVar(value="")
category_forbidden_frame = ttk.LabelFrame(right_col, text="카테고리 금칙어 파일 선택 (선택 사항)")
category_forbidden_frame.pack(fill="x", pady=(0, 10))

ttk.Button(
    category_forbidden_frame,
    text="카테고리 금칙어 파일 선택 (*.txt)",
    command=lambda: select_keyword_file(category_forbidden_path_var, category_path_label, "카테고리 금칙어")
).pack(anchor="w", padx=5, pady=5)

category_path_label = ttk.Label(category_forbidden_frame, wraplength=400, foreground="blue")
category_path_label.pack(anchor="w", padx=5, pady=(0, 5))




brand_forbidden_path_var = tk.StringVar(value="")

brand_forbidden_frame = ttk.LabelFrame(right_col, text="브랜드 금칙어 파일 선택 (선택 사항)")
brand_forbidden_frame.pack(fill="x", pady=(0, 10))

ttk.Button(
    brand_forbidden_frame,
    text="브랜드 금칙어 파일 선택 (*.txt)",
    command=lambda: select_keyword_file(brand_forbidden_path_var, brand_path_label, "브랜드 금칙어")
).pack(anchor="w", padx=5, pady=5)

brand_path_label = ttk.Label(brand_forbidden_frame, wraplength=400, foreground="blue")
brand_path_label.pack(anchor="w", padx=5, pady=(0, 5))






# 🔹 key_entry 만든 바로 아래에 추가
saved_key = load_saved_api_key()
if saved_key:
    key_entry.insert(0, saved_key)  # 저장된 키를 자동으로 입력칸에 넣어줌
    api_key=saved_key

# 7. 실행 / 중단 버튼
button_frame = ttk.Frame(right_col)
button_frame.pack(fill="x", pady=(10, 0))

def start_fresh():
    # 1페이지부터 시작하기
    # ✅ 이어하기 기록 삭제 + 시작페이지를 1로 강제 세팅(원하면)
    try:
        if os.path.exists(RESUME_STATE_FILE):
            os.remove(RESUME_STATE_FILE)
            gui_log("[INFO] 이어하기 기록 삭제 완료 → 시작페이지부터 수집합니다.")
    except Exception as e:
        gui_log(f"[WARN] 이어하기 기록 삭제 실패: {e}")

    start_collect(use_resume=False)

def start_resume():
    # 중단된곳부터 이어하기
    start_collect(use_resume=True)



start_fresh_btn = tk.Button(button_frame, text="시작페이지부터 수집하기", command=start_fresh, bg="blue", fg="white")
start_fresh_btn.pack(side="left", padx=(0, 10))

start_resume_btn = ttk.Button(button_frame, text="중단된곳부터 이어하기", command=start_resume)
start_resume_btn.pack(side="left", padx=(0, 10))


stop_button = ttk.Button(button_frame, text="중단하기", command=stop_collect)
stop_button.pack(side="left")

# --- ⭐ 8. 로그 창 섹션 추가 ---
log_frame = ttk.LabelFrame(right_col, text="로그 창")
log_frame.pack(fill="both", expand=True, pady=(10, 0)) # fill="both"와 expand=True로 공간을 채웁니다.



# 로그 출력을 위한 텍스트 위젯
log_text = tk.Text(log_frame, wrap=tk.WORD, height=10, state='normal')
log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

# 스크롤바 추가
log_scrollbar = ttk.Scrollbar(log_frame, command=log_text.yview)
log_scrollbar.pack(side="right", fill="y")
log_text.config(yscrollcommand=log_scrollbar.set)



# ✅ 로그 전체 복사 버튼 추가
copy_btn = ttk.Button(log_frame, text="로그 전체 복사", command=copy_log_to_clipboard)
copy_btn.pack(anchor="e", padx=5, pady=5)



window_id = canvas.create_window((0, 0), window=main_frame, anchor="nw")

def _on_canvas_configure(event):
    canvas.itemconfig(window_id, width=event.width)

canvas.bind("<Configure>", _on_canvas_configure)

def auto_fit_to_content():
    root.update_idletasks()
    bbox = canvas.bbox("all")  # (x1, y1, x2, y2)
    if not bbox:
        return
    content_w = bbox[2] - bbox[0] + 30
    content_h = bbox[3] - bbox[1] + 30

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w = min(content_w, int(sw * 0.98))
    h = min(content_h, int(sh * 0.92))

    root.geometry(f"{w}x{h}")

# mainloop 전에
auto_fit_to_content()



# --- 로그 창 섹션 끝 ---

if __name__ == "__main__":
    root.mainloop()




