@echo off
chcp 65001 > nul
cls
echo.
echo ========================================================================
echo 🔐 مولد مفاتيح التفعيل - HyperPOS V2 License Key Generator
echo ========================================================================
echo.
set /p HARDWARE_ID="أدخل سريال الجهاز (Hardware ID): "

if "%HARDWARE_ID%"=="" (
    echo.
    echo ❌ لم يتم إدخال سريال الجهاز
    echo.
    pause
    exit /b 1
)

python activate_license.py "%HARDWARE_ID%"

echo.
echo ========================================================================
echo.
pause
