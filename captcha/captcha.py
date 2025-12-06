
import time
import random
from openai import OpenAI
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.alert import Alert

from captcha.api import (
    save_api_key_to_file,
    apply_api_key
)


###############################################################
# 3. 캡챠 이미지 Base64 안정적으로 로딩
###############################################################
def get_captcha_image_base64(driver,CLICK_DELAY_RANGE):
    """
    rcpt_img가 로딩될 때까지 반복 확인하며 base64 추출.
    """
    for _ in range(30):  # 최대 30회(약 6초)
        try:
            img_tag = driver.find_element(By.ID, "rcpt_img")
            src = img_tag.get_attribute("src")

            if src and "base64," in src:
                return src.split("base64,")[1]
        except:
            pass

        time.sleep(random.uniform(*CLICK_DELAY_RANGE))

    raise Exception("ERROR: 캡챠 이미지 base64 로딩 실패")


###############################################################
# 4. Vision으로 캡챠 풀기 (오직 정답만)
###############################################################
def solve_captcha(question_text, img_base64,client,api_key):


    # ✅ 아직 client 안 만들어졌으면, GUI에서 API Key 읽어서 생성
    if client is None:
        
        if not api_key:
            raise RuntimeError(
                "API Key가 비어 있습니다.\n"
                "GUI의 [API Key 입력] 칸에 키를 넣고 다시 시도하세요."
            )
        client = OpenAI(api_key=api_key)
        save_api_key_to_file(api_key)
    prompt = (
        "이미지와 문제를 기반으로 정답만 출력하라.\n"
        "문장은 금지.\n"
        "설명 금지.\n"
        "-입니다 -다 -합니다 금지.\n"
        "정답만 출력.\n"
        "숫자 또는 단어만 출력.\n"
        f"문제: {question_text}"
    )

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                ]
            }
        ]
    )

    answer = response.choices[0].message.content.strip()

    # 불필요한 문장, 공백 제거
    answer = answer.replace("\n", "").strip()

    # 만약 공백이 포함되어 있고 문장이면 → 첫 단어만 사용
    if (" " in answer) and (not answer.isdigit()):
        answer = answer.split()[0]

    print("[INFO] Vision 정답 =", answer)
    return answer


###############################################################
# 5. 실패 검출 (오류문구 + 이미지 변경)
###############################################################
###############################################################
# 5. 실패 검출 (로직 강화)
###############################################################
def check_fail(before_img,driver):
    """
    [True 반환] -> 실패 (재시도 필요)
    [False 반환] -> 성공 (다음 단계로)
    """
    time.sleep(2.5)  # <--- 중요: 서버 응답 및 DOM 업데이트 대기 시간을 2.5초로 늘림

    # 1) [Alert 창 감지] 브라우저 경고창이 떴다면 실패
    try:
        from selenium.webdriver.common.alert import Alert
        alert = driver.switch_to.alert
        print(f"[DEBUG] Alert 감지됨: {alert.text}")
        alert.accept()  # 확인 버튼 누름
        return True     # 실패 처리
    except:
        pass

    # 2) [입력창 초기화 감지] 가장 강력한 힌트
    # 방금 값을 입력했는데, 현재 value가 비어있다면 실패해서 리셋된 것임.
    try:
        input_box = driver.find_element(By.ID, "rcpt_answer")
        current_val = input_box.get_attribute("value")
        
        # 입력창이 여전히 화면에 보이고 + 값이 비어있다면 -> 실패
        if input_box.is_displayed() and current_val == "":
            print("[DEBUG] 입력창이 비워짐(Reset) → 실패")
            return True
    except:
        # 입력창을 찾을 수 없음 -> 캡챠가 사라짐 -> 성공일 가능성 높음
        pass

    # 3) [이미지 변경 감지]
    try:
        after_element = driver.find_element(By.ID, "rcpt_img")
        after_src = after_element.get_attribute("src")
        after_img = after_src.split("base64,")[1] if "base64," in after_src else ""

        if after_img != before_img:
            print("[DEBUG] 캡챠 이미지가 변경됨 → 실패")
            return True
    except:
        pass

    # 4) [에러 문구 감지]
    try:
        msg_el = driver.find_element(By.ID, "rcpt_info")
        msg = msg_el.text.strip()
        # 문구가 비어있지 않고, 초기 안내 문구와 다르거나 부정적인 단어 포함 시
        if msg and any(k in msg for k in ["틀렸", "다시", "일치", "오류", "확인"]):
            print(f"[DEBUG] 실패 문구 감지: {msg}")
            return True
    except:
        pass

    # 위 실패 조건들에 걸리지 않았다면 성공으로 간주
    return False



###############################################################
# 6. 전체 시도 루프 (성공/실패 판별 로직 개선)
###############################################################
def try_captcha(driver,client,MAX_RETRY,CLICK_DELAY_RANGE,api_key=None):

    for attempt in range(1, MAX_RETRY + 1):
        print(f"\n[TRY] {attempt}번째 시도")

        # 1. 캡챠 영역 존재 확인 (이미 성공해서 없으면 종료)
        try:
            driver.find_element(By.ID, "rcpt_img")
        except:
            print("[SUCCESS] 캡챠가 없습니다. 이미 성공했습니다!")
            return True

        # 2. 문제 텍스트 및 이미지 가져오기
        try:
            question_text = driver.find_element(By.ID, "rcpt_info").text.strip()
        except:
            question_text = ""
        
        before_img = get_captcha_image_base64(driver,CLICK_DELAY_RANGE)

        # 3. Vision 정답 추출
        answer = solve_captcha(question_text, before_img,client,api_key)
        if not answer:
            print("[WARN] 정답 추출 실패, 새로고침 후 재시도")
            try: driver.find_element(By.ID, "cpt_refresh").click()
            except: pass
            time.sleep(7)
            continue

        # 4. 입력 및 제출
        try:
            input_box = driver.find_element(By.ID, "rcpt_answer")
            input_box.clear()
            input_box.send_keys(answer)
            
            confirm_btn = driver.find_element(By.ID, "cpt_confirm") # 확인 버튼 ID
            confirm_btn.click()
        except Exception as e:
            print(f"[ERROR] 입력/제출 중 오류: {e}")
            continue

        # 5. [핵심 수정] 결과 판별 (3초 대기)
        time.sleep(7) 

        # (A) Alert(경고창)이 떴는지 먼저 확인 (틀렸을 때 주로 뜸)
        try:
            from selenium.webdriver.common.alert import Alert
            alert = driver.switch_to.alert
            print(f"[FAIL] 경고창 뜸: {alert.text}")
            alert.accept()
            # 경고창이 떴다는 건 100% 실패 -> 다음 루프로
            continue 
        except:
            pass

        # (B) 캡챠 입력창이 "여전히 존재하는가?" 확인
        try:
            # 3초가 지났는데도 입력창을 찾을 수 있다? -> 아직 페이지가 안 넘어감 -> 실패!
            remain_input = driver.find_element(By.ID, "rcpt_answer")
            
            # 값을 확인해봅니다 (틀리면 보통 지워짐)
            if remain_input.get_attribute("value") == "":
                print("[FAIL] 입력창이 비워짐 (오답)")
            else:
                print("[FAIL] 페이지가 넘어가지 않음 (오답 가능성 높음)")
                
            # 실패했으니 이미지 새로고침 버튼 누르고 재시도
            try: driver.find_element(By.ID, "cpt_refresh").click()
            except: pass
            time.sleep(3)
            continue # 다음 for문(attempt)으로 이동

        except:
            # (C) 입력창을 찾을 수 없음 (에러 발생) -> 요소가 사라짐 -> 성공!
            print("[SUCCESS] 입력창이 사라졌습니다. (성공!)")
            return True

    print("[ERROR] 모든 재시도 실패")
    return False



# =======================================================
def is_captcha_page(driver):
    """
    현재 페이지가 캡챠(보안문자) 페이지인지 대략 판별.
    - title 에 'captcha', 'capcha' 같은 단어가 있는지
    - rcpt_img / rcpt_answer 같은 요소가 있는지
    """
    # 1) 페이지 title 체크
    try:
        title = (driver.title or "").lower()
        if "captcha" in title or "capcha" in title:
            return True
    except Exception:
        pass

    # 2) 대표적인 캡챠 요소(id)들 체크
    for elem_id in ("rcpt_img", "rcpt_answer", "cpt_confirm"):
        try:
            driver.find_element(By.ID, elem_id)
            return True
        except NoSuchElementException:
            continue
        except Exception:
            continue

    return False

def handle_captcha_if_needed(driver,client,MAX_RETRY,CLICK_DELAY_RANGE,api_key):
    """
    캡챠 페이지가 뜬 경우:
    - 한 번 감지되면, 사용자에게 직접 풀라고 안내
    - 사용자가 해결하고 엔터를 누르면 다시 확인
    - 여전히 캡챠면 False 반환 (이 링크/스토어는 스킵)
    - 캡챠가 사라졌으면 True 반환 (계속 진행)
    """
    if not is_captcha_page(driver):
        return True  # 평상시 페이지

    print("\n[주의] 캡챠(보안문자) 페이지가 감지되었습니다.")
    try_captcha(driver,client,MAX_RETRY,CLICK_DELAY_RANGE,api_key)

    # 다시 한 번 확인
    if is_captcha_page(driver):
        print("[WARN] 여전히 캡챠 페이지입니다. 이 링크/스토어는 건너뜁니다.")
        return False

    print("[INFO] 캡챠가 사라졌습니다. 계속 진행합니다.")
    return True

