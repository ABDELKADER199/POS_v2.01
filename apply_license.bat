@echo off
chcp 65001 > nul
cls
echo.
echo ========================================================================
echo ✨ تطبيق التفعيل - HyperPOS V2 License Activation
echo ========================================================================
echo.
set /p ACTIVATION_KEY="أدخل مفتاح التفعيل (Activation Key): "

if "%ACTIVATION_KEY%"=="" (
    echo.
    echo ❌ لم يتم إدخال مفتاح التفعيل
    echo.
    pause
    exit /b 1
)

python activate_and_apply.py "%ACTIVATION_KEY%"

echo.
echo ========================================================================
echo.
pause
