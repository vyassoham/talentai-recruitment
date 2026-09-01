@echo off
echo =======================================
echo    Starting TalentAI Recruiter App...
echo =======================================
echo.
echo Starting local interface, please wait...
cd /d D:\recruitment_platform\frontend
start /b npm run dev >nul 2>&1
timeout /t 5 /nobreak >nul
echo Opening App...
start chrome --app=http://localhost:3000
exit
