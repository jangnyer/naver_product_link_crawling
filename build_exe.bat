@echo off
echo ========================================
echo Starting exe build
echo ========================================

REM Install PyInstaller and runtime dependencies
python -m pip install pyinstaller
python -m pip install -r requirements.txt

REM Build single-file GUI exe
python -m PyInstaller --onefile --windowed --name="naver_product_link_crawling" --add-data "captcha;captcha" --add-data "crawling;crawling" --hidden-import=captcha.captcha --hidden-import=captcha.api --hidden-import=crawling.output_save.output_save --hidden-import=crawling.output_save.utills --hidden-import=selenium --hidden-import=undetected_chromedriver --hidden-import=openai --hidden-import=pandas --hidden-import=openpyxl --hidden-import=tkinter --collect-all=selenium --collect-all=undetected_chromedriver --exclude-module=torch --exclude-module=torchvision --exclude-module=torchaudio --exclude-module=tensorboard --exclude-module=scipy main.py

echo ========================================
echo Build complete.
echo Check dist\naver_product_link_crawling.exe
echo ========================================
pause
