@echo off
chcp 65001 > nul
cls
echo.
echo ========================================================================
echo ➕ إضافة مستخدم جديد - Add New User
echo ========================================================================
echo.

set /p NAME="أدخل اسم المستخدم: "
set /p EMAIL="أدخل البريد الإلكتروني: "
set /p PASSWORD="أدخل كلمة المرور: "
set /p ROLE="أدخل الدور (cashier/admin/manager) [افتراضي: cashier]: "

if "%ROLE%"=="" (
    set ROLE=cashier
)

if "%NAME%"=="" (
    echo.
    echo ❌ لم يتم إدخال الاسم
    echo.
    pause
    exit /b 1
)

if "%EMAIL%"=="" (
    echo.
    echo ❌ لم يتم إدخال البريد
    echo.
    pause
    exit /b 1
)

if "%PASSWORD%"=="" (
    echo.
    echo ❌ لم يتم إدخال كلمة المرور
    echo.
    pause
    exit /b 1
)

python add_user.py "%NAME%" "%EMAIL%" "%PASSWORD%" "%ROLE%"

echo.
echo ========================================================================
echo.
pause
