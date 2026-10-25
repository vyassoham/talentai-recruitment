@echo off
title TalentAI — Enterprise Recruitment
echo Launching TalentAI Cloud Application...

:: Launch dedicated standalone app window connected directly to the 24/7 online server
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app="https://talentai-recruiter.vercel.app/"
) else if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files\Microsoft\Edge\Application\msedge.exe" --app="https://talentai-recruiter.vercel.app/"
) else if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="https://talentai-recruiter.vercel.app/"
) else (
    start "" "https://talentai-recruiter.vercel.app/"
)
exit
