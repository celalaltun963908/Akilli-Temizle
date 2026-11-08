@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Akilli Temizle - Windows EXE olusturuluyor...
py -3 -m venv .venv
if errorlevel 1 goto fail
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto fail
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto fail
python -m PyInstaller --noconfirm --clean --onefile --windowed --name AkilliTemizle --collect-all fitz --collect-all pymupdf arayuz.py
if errorlevel 1 goto fail
echo.
echo TAMAMLANDI: dist\AkilliTemizle.exe
pause
exit /b 0
:fail
echo EXE olusturulamadi. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
