import sys
sys.path.append(r'd:\Python Desktop\POS_V2')
from controllers.admin_controller import AdminController
from services.audit_service import AuditService

def test_audit():
    audit_svc = AuditService()
    print("Testing Audit Log...")
    audit_svc.log(
        user_id=1,
        action="TEST_ACTION",
        entity_type="Invoice",
        entity_id="1005",
        store_id=1,
        success=True,
        details={"status": "completed", "amount": 500}
    )
    print("Log inserted.")
    
    ctrl = AdminController()
    logs = ctrl.get_audit_logs(limit=5)
    print(f"Fetched {len(logs)} logs.")
    for log in logs:
        print(f"[{log['created_at']}] User: {log['user_name']}, Action: {log['action']}, Entity: {log['entity_type']}:{log['entity_id']}, Details: {log['details']}")

if __name__ == '__main__':
    test_audit()
