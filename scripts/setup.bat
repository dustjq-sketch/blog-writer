@echo off
echo ========================================
echo  Blog Engine Setup
echo ========================================

REM Python venv 생성
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Python venv 생성 실패. Python 3.11 이상이 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)

REM 패키지 설치
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] 패키지 설치 실패.
    pause
    exit /b 1
)

REM .env 파일 복사 (없을 경우)
if not exist .env (
    copy .env.example .env
    echo [OK] .env 파일 생성됨. API 키를 입력해주세요: .env
)

REM data 폴더 생성
if not exist data\topics mkdir data\topics
if not exist data\collected mkdir data\collected
if not exist data\discarded mkdir data\discarded
if not exist data\pending_review mkdir data\pending_review
if not exist data\published mkdir data\published
if not exist data\analytics mkdir data\analytics
if not exist data\images mkdir data\images
if not exist data\drafts mkdir data\drafts
if not exist logs mkdir logs

REM Windows 작업 스케줄러에 scheduler.py 등록
set SCRIPT_PATH=%~dp0bots\scheduler.py
set PYTHON_PATH=%~dp0venv\Scripts\pythonw.exe

schtasks /query /tn "BlogEngine" >nul 2>&1
if errorlevel 1 (
    schtasks /create /tn "BlogEngine" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc onlogon /rl highest /f
    echo [OK] Windows 작업 스케줄러에 BlogEngine 등록 완료
) else (
    echo [INFO] BlogEngine 작업이 이미 등록되어 있습니다.
)

echo.
echo ========================================
echo  Setup 완료!
echo ========================================
echo.
echo 다음 단계:
echo 1. .env 파일을 열고 API 키를 모두 입력하세요
echo 2. scripts\get_token.py 를 실행해서 Google OAuth 토큰을 발급받으세요
echo 3. config\blogs.json 에서 BLOG_MAIN_ID 를 실제 블로그 ID로 변경하세요
echo 4. python bots\scheduler.py 로 스케줄러를 시작하세요
echo.
pause
