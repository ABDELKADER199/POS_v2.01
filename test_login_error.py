import sys
sys.path.append(r'd:\Python Desktop\POS_V2')
from application.services.auth_service_facade import get_auth_service

try:
    svc = get_auth_service()
    user = svc.login("admin@hyperpos.com", "Admin@123")
    print("User logged in:", user)
except Exception as e:
    import traceback
    traceback.print_exc()
