# 🔐 نظام التفعيل التفاعلي - HyperPOS V2
# License System Interactive Menu

function Show-Menu {
    Write-Host "`n"
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host "🔐 نظام التفعيل - HyperPOS V2 License System" -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1) 🔑 توليد مفتاح التفعيل (Generate Activation Key)" -ForegroundColor Yellow
    Write-Host "2) ✨ تطبيق مفتاح التفعيل (Apply Activation Key)" -ForegroundColor Yellow
    Write-Host "3) 🔍 التحقق من حالة التفعيل (Check Activation Status)" -ForegroundColor Yellow
    Write-Host "4) 📖 عرض التعليمات (Show Help)" -ForegroundColor Yellow
    Write-Host "5) ❌ خروج (Exit)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Generate-Key {
    Write-Host ""
    Write-Host "🔑 توليد مفتاح التفعيل" -ForegroundColor Green
    Write-Host "========================" -ForegroundColor Green
    Write-Host ""
    $hardwareId = Read-Host "أدخل سريال الجهاز (Hardware ID)"
    
    if ([string]::IsNullOrWhiteSpace($hardwareId)) {
        Write-Host "❌ لم يتم إدخال سريال الجهاز" -ForegroundColor Red
        return
    }
    
    Write-Host ""
    Write-Host "جاري توليد المفتاح..." -ForegroundColor Cyan
    python activate_license.py "$hardwareId"
}

function Apply-Key {
    Write-Host ""
    Write-Host "✨ تطبيق مفتاح التفعيل" -ForegroundColor Green
    Write-Host "======================" -ForegroundColor Green
    Write-Host ""
    $activationKey = Read-Host "أدخل مفتاح التفعيل (Activation Key)"
    
    if ([string]::IsNullOrWhiteSpace($activationKey)) {
        Write-Host "❌ لم يتم إدخال مفتاح التفعيل" -ForegroundColor Red
        return
    }
    
    Write-Host ""
    Write-Host "جاري تطبيق التفعيل..." -ForegroundColor Cyan
    python activate_and_apply.py "$activationKey"
}

function Check-Status {
    Write-Host ""
    Write-Host "🔍 التحقق من حالة التفعيل" -ForegroundColor Green
    Write-Host "=========================" -ForegroundColor Green
    Write-Host ""
    
    try {
        Add-Type -Path "$PSScriptRoot\utils\license_manager.py" -ErrorAction Stop
        $script = @"
import sys
sys.path.insert(0, '.')
from utils.license_manager import LicenseManager
from application.services.license_service import LicenseService

hw_id = LicenseManager.get_hardware_id()
service = LicenseService()
is_active = service.is_activated()

print(f'سريال الجهاز: {hw_id}')
print(f'حالة التفعيل: {"✅ مفعّل" if is_active else "❌ غير مفعّل"}')
"@
        python -c $script
    } catch {
        Write-Host "❌ خطأ في التحقق من الحالة" -ForegroundColor Red
    }
}

function Show-Help {
    Write-Host ""
    Write-Host "📖 التعليمات" -ForegroundColor Green
    Write-Host "============" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. توليد المفتاح:" -ForegroundColor Yellow
    Write-Host "   - اختر الخيار 1 أو استخدم: python activate_license.py" -ForegroundColor Gray
    Write-Host "   - أدخل سريال الجهاز (Hardware ID)" -ForegroundColor Gray
    Write-Host "   - ستحصل على مفتاح التفعيل (Activation Key)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. تطبيق المفتاح:" -ForegroundColor Yellow
    Write-Host "   - اختر الخيار 2 أو استخدم: python activate_and_apply.py" -ForegroundColor Gray
    Write-Host "   - أدخل مفتاح التفعيل" -ForegroundColor Gray
    Write-Host "   - سيتم حفظ التفعيل في قاعدة البيانات" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. صيغة السريال والمفتاح:" -ForegroundColor Yellow
    Write-Host "   - يجب أن تكون بهذا الشكل: XXXX-XXXX-XXXX-XXXX" -ForegroundColor Gray
    Write-Host "   - مثال: 78BE-1F72-FC34-FAEA" -ForegroundColor Gray
    Write-Host ""
}

# Main loop
while ($true) {
    Show-Menu
    $choice = Read-Host "اختر رقم الخيار"
    
    switch ($choice) {
        "1" { Generate-Key }
        "2" { Apply-Key }
        "3" { Check-Status }
        "4" { Show-Help }
        "5" { 
            Write-Host ""
            Write-Host "شكراً لاستخدام نظام التفعيل! 👋" -ForegroundColor Green
            exit
        }
        default { Write-Host "❌ خيار غير صحيح" -ForegroundColor Red }
    }
    
    Write-Host ""
    Write-Host "اضغط أي مفتاح للمتابعة..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
