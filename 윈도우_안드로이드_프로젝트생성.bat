@echo off
chcp 65001 >nul
cd /d "%~dp0"
where npm >nul 2>nul || (echo Node.js LTS 설치 후 다시 실행하세요. & pause & exit /b 1)
call npm install || goto :fail
if not exist android (call npx cap add android || goto :fail)
call npx cap sync android || goto :fail
call npx cap open android || goto :fail
exit /b 0
:fail
echo 작업 실패. 오류 메시지를 확인하세요.
pause
exit /b 1
