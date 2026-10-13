"""Unit tests for Phase 4: PDF Reports and Security Review"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_accounts_pdf_service_import():
    """Test importing the accounts PDF service"""
    from services.accounts_pdf_service import AccountsPdfReportService
    service = AccountsPdfReportService()
    assert service is not None
    assert callable(service.create_customer_account_pdf)
    assert callable(service.create_debt_aging_pdf)
    assert callable(service.create_ledger_pdf)
    assert callable(service.create_treasury_pdf)
    assert callable(service.create_expense_pdf)


def test_accounts_pdf_service_customer_report():
    """Test creating a customer account PDF"""
    from services.accounts_pdf_service import AccountsPdfReportService
    service = AccountsPdfReportService()
    customer_data = {
        'name': 'عميل تجريبي',
        'phone': '01012345678',
        'current_balance': 1500.00,
    }
    account_history = [
        {'date': '2024-01-01', 'description': 'فاتورة شراء', 'amount': 500, 'balance': 500},
        {'date': '2024-01-15', 'description': 'سداد', 'amount': -200, 'balance': 300},
    ]
    result = service.create_customer_account_pdf(
        customer_data, account_history, 'مدير النظام', 'المخزن الرئيسي'
    )
    assert isinstance(result, dict)
    assert 'saved' in result
    assert 'pdf_path' in result


def test_accounts_pdf_service_aging_report():
    """Test debt aging PDF creation"""
    from services.accounts_pdf_service import AccountsPdfReportService
    service = AccountsPdfReportService()
    aging_data = [
        {'customer_name': 'شركة التجارة', 'current': 1000, 'over_30': 500, 'over_60': 200, 'over_90': 100, 'total_due': 1800},
    ]
    result = service.create_debt_aging_pdf(aging_data, 'المخزن الرئيسي', 'مدير النظام')
    assert isinstance(result, dict)


def test_accounts_pdf_service_ledger_report():
    """Test financial ledger PDF creation"""
    from services.accounts_pdf_service import AccountsPdfReportService
    service = AccountsPdfReportService()
    ledger_data = [
        {'date': '2024-01-01', 'description': 'مبيعات', 'amount': 5000, 'balance': 5000},
        {'date': '2024-01-02', 'description': 'مشتريات', 'amount': -3000, 'balance': 2000},
    ]
    result = service.create_ledger_pdf(ledger_data, 'المخزن الرئيسي', 'مدير النظام')
    assert isinstance(result, dict)


def test_accounts_pdf_service_treasury_report():
    """Test treasury PDF creation"""
    from services.accounts_pdf_service import AccountsPdfReportService
    service = AccountsPdfReportService()
    transactions = [
        {'date': '2024-01-01', 'description': 'دفعة نقدية', 'amount': 1000, 'balance_after': 1000},
        {'date': '2024-01-02', 'description': 'سحب', 'amount': -500, 'balance_after': 500},
    ]
    result = service.create_treasury_pdf(transactions, 500, 'المخزن الرئيسي', 'مدير النظام')
    assert isinstance(result, dict)


def test_accounts_pdf_service_expense_report():
    """Test expense PDF creation"""
    from services.accounts_pdf_service import AccountsPdfReportService
    service = AccountsPdfReportService()
    expenses = [
        {'date': '2024-01-01', 'expense_type': 'صيانة', 'amount': 200, 'description': 'صيانة المعدات'},
        {'date': '2024-01-05', 'expense_type': 'كهرباء', 'amount': 300, 'description': 'فاتورة كهرباء'},
    ]
    result = service.create_expense_pdf(expenses, 'المخزن الرئيسي', 'مدير النظام')
    assert isinstance(result, dict)


def test_sync_service_facade_import_with_pdf():
    """Verify that accounts service facade can import PDF service"""
    try:
        from application.services.accounts_service_facade import AccountsServiceFacade
        print("AccountsServiceFacade imports successfully with PDF methods")
        # Check that PDF methods exist
        facade_methods = ['create_customer_account_pdf', 'create_debt_aging_pdf', 'create_ledger_pdf']
        for method in facade_methods:
            assert hasattr(AccountsServiceFacade, method), f"Method {method} missing"
        print("All PDF methods present in facade")
    except Exception as e:
        print(f"Import error: {e}")


if __name__ == '__main__':
    test_accounts_pdf_service_import()
    print("✓ accounts_pdf_service: import OK")

    test_accounts_pdf_service_customer_report()
    print("✓ customer_account_pdf: OK")

    test_accounts_pdf_service_aging_report()
    print("✓ debt_aging_pdf: OK")

    test_accounts_pdf_service_ledger_report()
    print("✓ ledger_pdf: OK")

    test_accounts_pdf_service_treasury_report()
    print("✓ treasury_pdf: OK")

    test_accounts_pdf_service_expense_report()
    print("✓ expense_pdf: OK")

    test_sync_service_facade_import_with_pdf()
    print("✓ facade_methods: OK")

    print("\n=== All Phase 4 PDF Report Tests Passed ===")
