# -*- coding: utf-8 -*-
"""
통이미지 4개 랜덤 크롭 & 자동 폴더링 (Simple UI, Tkinter)
- UI 톤: 연한 회색 배경 + 흰 카드 + 파랑 포인트 (기존 유지)
- GUI 배치/크기: 기존 그대로 (1080x780)
- 개선 로직: 무결성 검사(verify + load) + 자동 재시도 + 원자적 저장(os.replace)
- 임시파일 확장자 이슈 해결: img.save(..., format="PNG")
- 재시도 대상/회차/결과를 모두 실시간 로그 및 logs/에 기록
"""

import os, io, sys, random, datetime, traceback, time
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from openpyxl import load_workbook

# ---- UI Palette ----
UI_BG = "#F5F7FA"
UI_FG = "#1F2937"
UI_CARD = "#FFFFFF"
UI_BORDER = "#E5E7EB"
UI_ACCENT = "#2563EB"
UI_FONT = ("맑은 고딕", 10)
UI_FONT_TITLE = ("맑은 고딕", 12, "bold")

# 핑크 배지(연한 핑크 + 진한 로즈 텍스트)
UI_PINK_BG = "#FFE4F2"
UI_PINK_FG = "#9D174D"

HELP_TEXT = (
    "[사용 방법]\n"
    "1) 엑셀 파일을 선택합니다.\n"
    "2) 원고 슬롯 4개에 이미지와 원고번호(1~4)를 입력합니다.\n"
    "3) [이미지 크롭·저장 실행]을 누릅니다.\n"
    "   - 파일명: 원고번호_오늘날짜_연속번호.png  (예: 1_251020_1.png)\n"
    "   - 여백이 없으면 스킵됩니다.\n"
    "4) [URL 생성]을 누르면 각 경로에 URL.txt가 생성됩니다."
)

# ===== VBA 동등 유틸 =====
def clean_seg(s: str) -> str:
    s = (s or "").strip()
    for ch in ['\\','/',':','*','?','"','<','>','|']:
        s = s.replace(ch, ' ')
    while len(s) > 0 and (s.endswith(' ') or s.endswith('.')):
        s = s[:-1]
    return s.strip()

def remove_spaces_tabs(s: str) -> str:
    return (s or "").replace(' ', '').replace('\t', '')

def parse_blog_cell(cell_text: str):
    s = (cell_text or '').strip()
    p_open = s.find('(')
    p_close = s.rfind(')')
    if p_open > -1 and p_close > p_open:
        blog_name = s[:p_open].strip()
        blog_id = s[p_open+1:p_close].strip()
    else:
        blog_name = s
        blog_id = ''
    return blog_name, blog_id

def blog_id_by_name(name: str) -> str:
    mapping = {
        "오늘갓생": "bride11231",
        "계단타기": "scold10151",
        "일단시작": "affair5459",
        "예쁨주의": "cap2417",
        "노력천재": "reserve1047",
        "글로우핏": "scarce8501",
        "슬림조이": "withpiano001",
        "살곰달곰": "kbshb72",
    }
    return mapping.get((name or '').strip(), '')

def ensure_folder(path: str):
    os.makedirs(path, exist_ok=True)

def write_text_utf8(full_path: str, content: str):
    ensure_folder(os.path.dirname(full_path))
    with io.open(full_path, 'w', encoding='utf-8') as f:
        f.write(content or '')

def to_date_folder_and_medium(v_date):
    import datetime as _dt
    try:
        if isinstance(v_date, _dt.datetime):
            d = v_date
        elif isinstance(v_date, _dt.date):
            d = _dt.datetime(v_date.year, v_date.month, v_date.day)
        else:
            s = str(v_date).strip()  # '10월 16일'
            d = _dt.datetime.strptime(s, "%m월 %d일")
            d = d.replace(year=_dt.datetime.now().year)
        date_folder = d.strftime("%y.%m.%d")
        medium = d.strftime("%y%m%d")
        return date_folder, medium
    except Exception:
        s = clean_seg(str(v_date).strip())
        medium = s.replace('.', '').replace('-', '')
        return s, medium

def today_yymmdd() -> str:
    return datetime.datetime.now().strftime("%y%m%d")

# ===== 무결성 검사 + 재시도 =====
def verify_image_integrity(path: str) -> bool:
    """
    저장된 PNG가 손상되지 않았는지 검사:
    1) 구조/CRC 확인(Image.verify)
    2) 전체 디코딩(Image.load)
    """
    try:
        from PIL import Image as _Image
        with _Image.open(path) as im:
            im.verify()
        with _Image.open(path) as im:
            im.load()
        return True
    except (OSError, UnidentifiedImageError):
        return False

def save_with_retry_and_integrity(img, target, logger, max_retries=10, delay=0.2):
    """
    PNG를 tmp에 저장(포맷 명시) → os.replace로 원자적 교체 → 무결성 검사
    실패 시 재시도. 모든 시도/결과는 logger로 남김.
    """
    tmp = target + ".tmp"
    attempt = 1
    while attempt <= max_retries:
        try:
            # ★ 핵심: 확장자 .tmp라도 Pillow가 포맷을 알 수 있게 format="PNG" 명시
            img.save(tmp, format="PNG", optimize=False)
            os.replace(tmp, target)

            # 저장 후 무결성 검사(verify + load)
            if verify_image_integrity(target):
                if attempt > 1:
                    logger(f"🩵 [정상복구] 재시도 {attempt-1}회 후 무결성 통과 → {target}")
                return True
            else:
                logger(f"⚠️ [무결성 실패] {attempt}회차 → {target}")
                attempt += 1
                time.sleep(delay)

        except Exception as e:
            logger(f"❌ [저장 실패] {attempt}회차 → {target} | {e}")
            attempt += 1
            time.sleep(delay)
        finally:
            # 실패 케이스에서 tmp 잔존 방지
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    logger(f"❌ [최대 재시도 초과] 손상된 파일 유지됨 → {target}")
    return False

# ===== 엑셀 읽기 (전체행) =====
def read_rows_from_excel(xlsx_path: str, logger):
    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = []
    for r in ws.iter_rows(min_row=1, values_only=True):
        if r is None or len(r) < 15:
            continue
        A = r[0]   # 날짜
        B = r[1]   # 키워드
        H = r[7]   # 블로그명(ID)
        O = r[14] if len(r) > 14 else ''
        if (A is None) and (B is None) and (H is None):
            continue

        blog_name_raw, blog_id = parse_blog_cell(H)
        if not blog_id:
            blog_id = blog_id_by_name(blog_name_raw)

        blog_name = "2. " + clean_seg(blog_name_raw)
        date_folder, medium = to_date_folder_and_medium(A)
        keyword_raw = (B or '')
        keyword_folder = clean_seg(keyword_raw)
        detail_param = remove_spaces_tabs(keyword_raw)

        vname = (O or '').strip()
        nt_keyword = vname if len(vname) == 2 else "소희"

        base_path = r"Z:\미드브로\❤ 마케팅\6.원고 이미지 교체 건"
        final_path = os.path.join(base_path, blog_name, date_folder, keyword_folder)

        url = (
            "http://innerium.co.kr/surl/p/18/?"
            f"utm_source={blog_id}/{detail_param}/{nt_keyword}/{medium}"
        )

        rows.append({
            "final_path": final_path,
            "url": url,
            "blog_name": blog_name,
            "date_folder": date_folder,
            "keyword_folder": keyword_folder,
            "medium": medium,
            "nt_keyword": nt_keyword
        })
    logger(f"ℹ️ [엑셀] 총 {len(rows)}행 로드 완료")
    return rows

# ===== 이미지 유틸 =====
def load_image_exif_oriented(path: str) -> Image.Image:
    """
    원본을 완전히 메모리로 로드하고 파일 핸들을 닫기 위해 copy 사용.
    (지연 로드/파일 락 영향 최소화)
    """
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        return im.copy()

def is_row_white(arr_row, thresh=250):
    return np.all(arr_row >= thresh)

def detect_top_bottom_white_margins(img: Image.Image, thresh=250):
    img_rgb = img.convert("RGB")
    arr = np.array(img_rgb)
    H, W, _ = arr.shape

    top_margin = 0
    for y in range(H):
        if is_row_white(arr[y, :, :], thresh):
            top_margin += 1
        else:
            break

    bottom_margin = 0
    for y in range(H-1, -1, -1):
        if is_row_white(arr[y, :, :], thresh):
            bottom_margin += 1
        else:
            break

    return top_margin, bottom_margin

def pick_random_cuts(top_margin, bottom_margin):
    if top_margin < 1 or bottom_margin < 1:
        return None, None
    top_cut = random.randint(1, top_margin)
    bottom_cut = random.randint(1, bottom_margin)
    return top_cut, bottom_cut

def next_available_filename(dirpath: str, base_name_no_ext: str, ext: str) -> str:
    seq = 1
    while True:
        candidate = f"{base_name_no_ext}_{seq}{ext}"
        full = os.path.join(dirpath, candidate)
        if not os.path.exists(full):
            return full
        seq += 1

# ===== 처리 로직 =====
def process_images_for_all_rows(excel_rows, slots, logger, progress_cb):
    valid = [(p, n) for (p, n) in slots if p and n in [1,2,3,4]]
    total_jobs = len(valid) * len(excel_rows)
    done = 0
    if total_jobs == 0:
        logger("ℹ️ [실행] 처리할 작업이 없습니다(이미지/원고번호 확인).")
        progress_cb(0)
        return

    today = today_yymmdd()

    for (img_path, wn) in valid:
        try:
            base_img = load_image_exif_oriented(img_path)
            W, H = base_img.size
            top_margin, bottom_margin = detect_top_bottom_white_margins(base_img, thresh=250)
            if top_margin < 1 or bottom_margin < 1:
                logger(f"⏭️ [스킵] 여백 없음/부족 → {os.path.basename(img_path)} "
                       f"(top={top_margin}, bottom={bottom_margin})")
                done += len(excel_rows)
                progress_cb(int(done*100/total_jobs))
                continue

            top_cut, bottom_cut = pick_random_cuts(top_margin, bottom_margin)
            if top_cut is None:
                logger(f"⏭️ [스킵] 랜덤 컷 불가(여백<1px) → {os.path.basename(img_path)}")
                done += len(excel_rows)
                progress_cb(int(done*100/total_jobs))
                continue

            L, T, R, B = 0, top_cut, W, H - bottom_cut
            if T >= B:
                logger(f"⏭️ [스킵] 크롭 범위 비정상(T>=B) → {os.path.basename(img_path)}")
                done += len(excel_rows)
                progress_cb(int(done*100/total_jobs))
                continue

            # PNG 저장 전 색모드 정규화된 크롭
            cropped = base_img.crop((L, T, R, B))

        except Exception as e:
            logger(f"❌ [에러] 이미지 로드/여백검출 실패: {os.path.basename(img_path)} | {e}")
            done += len(excel_rows)
            progress_cb(int(done*100/total_jobs))
            continue

        for row in excel_rows:
            try:
                final_dir = row["final_path"]
                ensure_folder(final_dir)
                base_no_ext = f"{wn}_{today}"
                target = next_available_filename(final_dir, base_no_ext, ".png")

                # === 개선된 저장: 무결성 검사 + 재시도 + 상세 로그 ===
                ok = save_with_retry_and_integrity(cropped, target, logger, max_retries=10, delay=0.2)
                if ok:
                    logger(f"✅ [성공] 무결성 통과: {target}")
                else:
                    logger(f"❌ [실패] 끝까지 무결성 확보 실패: {target}")

            except Exception as e:
                logger(f"❌ [에러] 저장 중 예외: {row['final_path']} | {os.path.basename(img_path)} | {e}")
            finally:
                done += 1
                progress_cb(int(done*100/total_jobs))

def generate_urls_for_all_rows(excel_rows, logger):
    """
    각 행 폴더에 URL.txt 생성

    내용 형식:
    1위 배합량 동일 

    (기존 저장하던 링크)

    https://smartstore.naver.com/globalreporter/products/9732262671?ref={weekday}{medium}?v=000001

    https://www.skstoa.com/display/goods/42990779?ref={weekday}{medium}?v=000001

    ※ 같은 키워드(같은 행)에서는 2위/3위의 v 값이 동일,
       다음 키워드로 넘어갈 때 v가 1씩 증가(000001, 000002, …)
    """
    cnt = 0

    # 오늘 요일(영어) - 예: Monday, Tuesday...
    today_weekday = datetime.datetime.now().strftime("%A")  # 영어 요일

    # 2·3위 고정 베이스 URL
    base2 = "https://smartstore.naver.com/globalreporter/products/9732262671"
    base3 = "https://www.skstoa.com/display/goods/42990779"

    v_counter = 1  # 키워드(행)별 v 값 카운터

    for row in excel_rows:
        try:
            dest_dir = row["final_path"]
            ensure_folder(dest_dir)

            # 기존 1위 링크
            link1 = row["url"]

            # medium(예: 251010)
            medium = str(row.get("medium", "")).strip()

            # 현재 키워드용 v 값 (6자리)
            v_str = f"{v_counter:06d}"  # 000001, 000002, ...

            # 2위 / 3위 링크 생성
            # 예: ?ref=monday251010?v=000001
            link2 = f"{base2}?ref={today_weekday.lower()}{medium}?v={v_str}"
            link3 = f"{base3}?ref={today_weekday.lower()}{medium}?v={v_str}"

            # 메모장 내용
            lines = [
                "1위 배합량 동일",
                "",
                link1,
                "",
                link2,
                "",
                link3,
                ""
            ]
            content = "\n".join(lines)

            full_path = os.path.join(dest_dir, "URL.txt")
            write_text_utf8(full_path, content)
            cnt += 1

            # 다음 키워드로 넘어갈 때 v + 1
            v_counter += 1

        except Exception as e:
            logger(f"❌ [에러] URL.txt 저장 실패: {row.get('final_path','?')} | {e}")

    logger(f"✅ [URL] 생성 완료: {cnt}개")



# ===== GUI =====
class App:
    def __init__(self, root):
        self.root = root
        root.title("통이미지 4개 크롭 & 자동 폴더링")
        root.geometry("1080x780")            # 기존 크기 그대로
        root.configure(bg=UI_BG)

        # ttk 스타일
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure("TLabel", background=UI_BG, foreground=UI_FG, font=UI_FONT)
        style.configure("TFrame", background=UI_BG)
        style.configure("TLabelframe", background=UI_BG, foreground=UI_FG)
        style.configure("TLabelframe.Label", background=UI_BG, foreground=UI_FG, font=UI_FONT)
        style.configure("TButton", font=UI_FONT, padding=6)
        style.configure("Card.TLabelframe", background=UI_CARD, relief="solid",
                        bordercolor=UI_BORDER, borderwidth=1)
        style.configure("Card.TLabelframe.Label", background=UI_CARD, foreground=UI_FG, font=UI_FONT)
        style.configure("Accent.Horizontal.TProgressbar", troughcolor="#EEF2FF", background=UI_ACCENT)

        # 상단 영역 (제목 + 설명: 항상 왼쪽 정렬)
        frm_top = ttk.Frame(root, style="TFrame")
        frm_top.pack(fill="x", padx=16, pady=12)
        tk.Label(frm_top, text="이미지 자동 크롭 & 폴더링", font=UI_FONT_TITLE, bg=UI_BG, fg=UI_FG)\
            .pack(anchor="w")
        tk.Label(frm_top, text=HELP_TEXT, font=UI_FONT, bg=UI_BG, fg=UI_FG,
                 justify="left", anchor="w")\
            .pack(fill="x", pady=(4,0), anchor="w")

        # 엑셀 선택 (핑크 배지 labelwidget 적용)
        frm_x_container = ttk.Frame(root, style="TFrame")
        frm_x_container.pack(fill="x", padx=16, pady=(6,12))

        xl_title = tk.Label(frm_x_container, text="엑셀 파일(전체행 사용)",
                            bg=UI_PINK_BG, fg=UI_PINK_FG,
                            font=("맑은 고딕", 10, "bold"), padx=8, pady=2)
        frm_x = ttk.LabelFrame(frm_x_container, labelwidget=xl_title,
                               style="Card.TLabelframe", padding=0)
        frm_x.pack(fill="x")

        inner_x = ttk.Frame(frm_x, padding=8, style="TFrame")
        inner_x.pack(fill="x")
        self.xlsx_var = tk.StringVar()
        ent = ttk.Entry(inner_x, textvariable=self.xlsx_var)
        ent.pack(side="left", fill="x", expand=True, padx=(0,6))
        ttk.Button(inner_x, text="찾기", command=self.pick_excel).pack(side="left")
        self.load_stat = tk.StringVar(value="엑셀 미선택")
        ttk.Label(inner_x, textvariable=self.load_stat).pack(side="left", padx=10)

        # 원고 슬롯 4개 (2x2) — 핑크 배지 labelwidget 사용
        frm_slots = ttk.Frame(root, style="TFrame")
        frm_slots.pack(fill="both", expand=True, padx=16, pady=6)
        for r in range(2): frm_slots.rowconfigure(r, weight=1)
        for c in range(2): frm_slots.columnconfigure(c, weight=1)

        self.slot_img_vars = []
        self.slot_no_vars = []
        slot_frames = []
        for i in range(1, 5):
            title = tk.Label(frm_slots, text=f"원고 슬롯 {i}",
                             bg=UI_PINK_BG, fg=UI_PINK_FG,
                             font=("맑은 고딕", 10, "bold"), padx=8, pady=2)
            f = ttk.LabelFrame(frm_slots, labelwidget=title, style="Card.TLabelframe", padding=0)
            slot_frames.append(f)

        slot_frames[0].grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        slot_frames[1].grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        slot_frames[2].grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        slot_frames[3].grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

        for i in range(1, 5):
            frame = slot_frames[i-1]
            inner = ttk.Frame(frame, padding=8, style="TFrame")
            inner.pack(fill="both", expand=True)

            row1 = ttk.Frame(inner, style="TFrame"); row1.pack(fill="x", pady=(2,4))
            ttk.Label(row1, text="이미지 파일:").pack(side="left")
            ivar = tk.StringVar(); self.slot_img_vars.append(ivar)
            e = ttk.Entry(row1, textvariable=ivar); e.pack(side="left", fill="x", expand=True, padx=6)
            ttk.Button(row1, text="선택", command=lambda v=ivar: self.pick_image(v)).pack(side="left")

            row2 = ttk.Frame(inner, style="TFrame"); row2.pack(fill="x")
            ttk.Label(row2, text="원고번호(1~4):").pack(side="left")
            nvar = tk.StringVar(value=str(i)); self.slot_no_vars.append(nvar)
            ttk.Spinbox(row2, from_=1, to=4, textvariable=nvar, width=5)\
                .pack(side="left", padx=(6, 0))

        # 액션 버튼 (가운데 정렬)
        frm_act_outer = ttk.Frame(root, style="TFrame")
        frm_act_outer.pack(fill="x", padx=16, pady=8)
        frm_act_inner = ttk.Frame(frm_act_outer, style="TFrame")
        frm_act_inner.pack()
        btn_run = ttk.Button(frm_act_inner, text="이미지 크롭·저장 실행", command=self.run_crop)
        btn_url = ttk.Button(frm_act_inner, text="URL 생성", command=self.run_url)
        btn_run.pack(side="left", padx=8, pady=2)
        btn_url.pack(side="left", padx=8, pady=2)

        # 진행률바: 라벨 + % 표시
        frm_prog = ttk.Frame(root, style="TFrame")
        frm_prog.pack(fill="x", padx=16, pady=(0,6))
        ttk.Label(frm_prog, text="진행률").pack(anchor="w")
        self.prog = ttk.Progressbar(frm_prog, style="Accent.Horizontal.TProgressbar",
                                    maximum=100, mode="determinate")
        self.prog.pack(fill="x")
        self.prog_pct = tk.StringVar(value="0%")
        tk.Label(frm_prog, textvariable=self.prog_pct, font=("맑은 고딕", 9),
                 bg=UI_BG, fg="#374151").pack(anchor="e", pady=(2,0))

        # 로그
        self.log = scrolledtext.ScrolledText(root, height=16)
        self.log.configure(bg="#FFFFFF", fg="#111827", font=("Consolas", 10))
        self.log.pack(fill="both", expand=True, padx=16, pady=6)

        # 상태
        self.excel_rows = []
        self.logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.log_file = os.path.join(self.logs_dir, datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt")

    def pick_excel(self):
        path = filedialog.askopenfilename(
            title="엑셀 파일 선택",
            filetypes=[("Excel", "*.xlsx *.xlsm *.xltx *.xltm")]
        )
        if not path:
            return
        self.xlsx_var.set(path)
        self.log_clear()
        self.prog_set(0)
        try:
            self.excel_rows = read_rows_from_excel(path, self.logger)
            self.load_stat.set(f"로드됨: {len(self.excel_rows)}행")
        except Exception as e:
            self.excel_rows = []
            self.load_stat.set("로드 실패")
            self.logger(f"❌ [에러] 엑셀 로드 실패: {e}")

    def pick_image(self, var: tk.StringVar):
        path = filedialog.askopenfilename(
            title="이미지 선택",
            filetypes=[("이미지", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp")]
        )
        if path:
            var.set(path)

    def run_crop(self):
        if not self.excel_rows:
            self.logger("ℹ️ [실행중단] 엑셀을 먼저 선택/로드하세요.")
            return
        slots = []
        for i in range(4):
            imgp = self.slot_img_vars[i].get().strip() or None
            try:
                wno = int((self.slot_no_vars[i].get() or "").strip())
            except:
                wno = None
            if wno not in [1,2,3,4]:
                if imgp:
                    self.logger(f"ℹ️ [알림] 슬롯{i+1}: 원고번호 1~4 아님 → 제외")
                slots.append((None, None))
            else:
                slots.append((imgp, wno))

        try:
            self.prog_set(0)
            self.logger("▶️ [실행] 이미지 크롭·저장 시작")
            process_images_for_all_rows(self.excel_rows, slots, self.logger, self.prog_set)
            self.logger("✅ [완료] 이미지 크롭·저장 끝")
        except Exception as e:
            self.logger(f"❌ [에러] 실행 중 예외: {e}\n{traceback.format_exc()}")
        finally:
            self.flush_log_to_file()

    def run_url(self):
        if not self.excel_rows:
            self.logger("ℹ️ [실행중단] 엑셀을 먼저 선택/로드하세요.")
            return
        try:
            self.logger("▶️ [URL] 생성 시작")
            generate_urls_for_all_rows(self.excel_rows, self.logger)
            self.logger("✅ [URL] 생성 끝")
        except Exception as e:
            self.logger(f"❌ [에러] URL 생성 중 예외: {e}")
        finally:
            self.flush_log_to_file()

    # ---- 로그/진행 ----
    def logger(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end", f"[{ts}] {msg}\n")
        self.log.see("end")
        self.log.config(state="disabled")
        self.root.update_idletasks()

    def log_clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def prog_set(self, percent: int):
        percent = max(0, min(100, int(percent)))
        self.prog['value'] = percent
        self.prog_pct.set(f"{percent}%")
        self.root.update_idletasks()

    def flush_log_to_file(self):
        try:
            content = self.log.get("1.0", "end")
            with io.open(self.log_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
