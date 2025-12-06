import os
import time
import random
from tkinter import messagebox
from openai import OpenAI
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.alert import Alert

API_KEY_FILE = "api_key.txt" 


def apply_api_key(key_entry):
    global client
    key = key_entry.get().strip()
    if not key:
        messagebox.showerror("에러", "API Key를 입력해주세요.")
        return
    client = OpenAI(api_key=key)
    print("[INFO] API Key 설정 완료")

def save_api_key_to_file(api_key: str):
    """API Key를 텍스트 파일에 저장 (다음 실행 때 자동 사용)"""
    try:
        with open(API_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(api_key.strip())
        print("[INFO] API Key 를 파일에 저장했습니다. (다음 실행 때 자동으로 불러옵니다.)")
    except Exception as e:
        print(f"[WARN] API Key 저장 실패: {e}")


def load_saved_api_key():
    """이전에 저장한 API Key가 있으면 읽어서 문자열로 반환"""
    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""
    return ""