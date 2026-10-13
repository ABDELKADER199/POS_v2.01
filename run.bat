@echo off
chcp 65001 > nul
cls
echo.
echo ========================================================================
echo 🚀 HyperPOS V2 - تشغيل البرنامج
echo ========================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Python غير مثبت على جهازك
    echo لتحميل Python، اذهب إلى: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Check if MySQL is running
echo ⏳ جاري التحقق من الاتصال بقاعدة البيانات...
python -c "from repositories.db_connection import DatabaseConnection; db = DatabaseConnection(); print('✅ قاعدة البيانات متصلة')" >nul 2>&1

if errorlevel 1 (
    echo.
    echo ❌ خطأ في الاتصال بقاعدة البيانات
    echo تأكد من:
    echo   1. MySQL قيد التشغيل
    echo   2. بيانات الاتصال صحيحة في ملف .env
    echo.
    pause
    exit /b 1
)

echo ✅ قاعدة البيانات متصلة

REM Check if user exists
echo.
echo ⏳ جاري التحقق من وجود مستخدمين...
python check_users.py >nul 2>&1

if errorlevel 1 (
    echo.
    echo ⚠️  لا توجد مستخدمون!
    echo جاري إنشاء مستخدم إداري افتراضي...
    python setup_default_user.py
)

echo.
echo ========================================================================
echo 🚀 جاري تشغيل HyperPOS V2...
echo ========================================================================
echo.

python main.py

echo.
echo ========================================================================
echo شكراً لاستخدام HyperPOS V2
echo ========================================================================
echo.
pause
