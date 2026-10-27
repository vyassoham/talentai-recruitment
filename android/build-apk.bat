@echo off
setlocal
echo ========================================================
echo       TalentAI Enterprise Mobile APK Build System       
echo ========================================================
echo.

set JAVA_HOME=C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot
set ANDROID_HOME=D:\Development\SDKs\Android\Sdk
set GRADLE_USER_HOME=D:\Development\SDKs\Android\.gradle

set GRADLE_BIN=D:\Development\SDKs\Android\.gradle\wrapper\dists\gradle-8.9-bin\90cnw93cvbtalezasaz0blq0a\gradle-8.9\bin\gradle.bat

cd /d "%~dp0"

echo [1/3] Cleaning previous build outputs...
call "%GRADLE_BIN%" clean

echo.
echo [2/3] Building signed release APK...
call "%GRADLE_BIN%" :app:assembleRelease

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed! Check gradle logs above.
    exit /b 1
)

echo.
echo [3/3] Copying APK to root platform directory...
copy /Y "app\build\outputs\apk\release\app-release.apk" "..\TalentAI-v1.0.1.apk"

echo.
echo ========================================================
echo [SUCCESS] APK built successfully:
echo Path: D:\recruitment_platform\TalentAI-v1.0.1.apk
echo ========================================================
