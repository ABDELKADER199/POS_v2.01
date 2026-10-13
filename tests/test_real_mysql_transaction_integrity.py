import os
import threading
import pytest
import mysql.connector
from dotenv import load_dotenv

from repositories.db_connection import DatabaseConnection
from repositories.invoice_repo import InvoiceRepository
from repositories.inventory_repo import InventoryRepository
from repositories.returns_repo import ReturnsRepository
from application.migration_runner import MigrationRunner
from application.use_cases.cashier_cart import CashierCartUseCase
from application.use_cases.checkout_sale import CheckoutSaleUseCase
from application.use_cases.returns import ProcessReturnUseCase
from models.product import Product

load_dotenv()

DISPOSABLE_DB_NAME = "disposable_pos_audit_test"


def get_raw_mysql_conn():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password=os.getenv("POS_DB_PASSWORD", ""),
            autocommit=True,
        )
    except Exception as err:
        pytest.skip(f"MySQL connection not available: {err}")


@pytest.fixture
def disposable_mysql():
    conn = get_raw_mysql_conn()
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {DISPOSABLE_DB_NAME}")
    cur.execute(
        f"CREATE DATABASE {DISPOSABLE_DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"USE {DISPOSABLE_DB_NAME}")

    # إنشاء الجداول الأساسية
    cur.execute("""
    CREATE TABLE stores (
        id INT PRIMARY KEY AUTO_INCREMENT,
        store_name VARCHAR(100) NOT NULL
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE roles (
        id INT PRIMARY KEY AUTO_INCREMENT,
        role_name VARCHAR(50) NOT NULL
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE users (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL,
        password VARCHAR(255) NOT NULL DEFAULT '',
        role_id INT NULL,
        store_id INT NOT NULL
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE products (
        id INT PRIMARY KEY AUTO_INCREMENT,
        product_code VARCHAR(50) NOT NULL,
        product_name VARCHAR(150) NOT NULL,
        buy_price DECIMAL(10,2) NOT NULL,
        sell_price DECIMAL(10,2) NOT NULL,
        tax_percent DECIMAL(5,2) DEFAULT 0
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE product_inventory (
        id INT PRIMARY KEY AUTO_INCREMENT,
        product_id INT NOT NULL,
        store_id INT NOT NULL,
        quantity_in_stock DECIMAL(12,3) NOT NULL DEFAULT 0,
        UNIQUE KEY uq_prod_store (product_id, store_id)
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE customers (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL,
        phone VARCHAR(20),
        address TEXT,
        current_balance DECIMAL(12,2) DEFAULT 0,
        credit_limit DECIMAL(12,2) DEFAULT 0
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE invoices (
        id INT PRIMARY KEY AUTO_INCREMENT,
        invoice_number VARCHAR(50) NOT NULL UNIQUE,
        store_id INT NOT NULL,
        cashier_id INT NOT NULL,
        customer_id INT,
        customer_name VARCHAR(100),
        customer_phone VARCHAR(20),
        customer_address TEXT,
        drawer_id INT,
        invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount DECIMAL(12, 2) NOT NULL,
        paid_amount DECIMAL(12, 2),
        remaining_amount DECIMAL(12, 2),
        cash_amount DECIMAL(12, 2) DEFAULT 0,
        card_amount DECIMAL(12, 2) DEFAULT 0,
        subtotal_amount DECIMAL(12, 2) DEFAULT 0,
        tax_amount DECIMAL(12, 2) DEFAULT 0,
        payment_method VARCHAR(20) DEFAULT 'Cash',
        discount_company_id INT NULL,
        discount_company_name VARCHAR(150) NULL,
        company_discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
        status VARCHAR(20) DEFAULT 'Completed'
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE invoice_items (
        id INT PRIMARY KEY AUTO_INCREMENT,
        invoice_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity DECIMAL(12,3) NOT NULL,
        unit_price DECIMAL(10, 2) NOT NULL,
        discount DECIMAL(10, 2) DEFAULT 0,
        total_price DECIMAL(12, 2) NOT NULL,
        buy_price DECIMAL(10,2) DEFAULT 0,
        item_subtotal DECIMAL(12,2) DEFAULT 0,
        item_tax DECIMAL(12,2) DEFAULT 0,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE treasury (
        id INT PRIMARY KEY AUTO_INCREMENT,
        store_id INT NOT NULL,
        user_id INT NOT NULL,
        transaction_type VARCHAR(20) NOT NULL,
        amount DECIMAL(12,2) NOT NULL,
        description VARCHAR(255),
        source_type VARCHAR(30),
        source_id INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE financial_ledger (
        id INT PRIMARY KEY AUTO_INCREMENT,
        account_type VARCHAR(50),
        account_id INT,
        amount DECIMAL(12,2),
        transaction_type VARCHAR(50),
        description TEXT,
        reference_id INT,
        store_id INT NULL,
        balance_before DECIMAL(12,2) NULL,
        balance_after DECIMAL(12,2) NULL,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE tax_customer_details (
        id INT PRIMARY KEY AUTO_INCREMENT,
        invoice_id INT,
        company_name VARCHAR(150),
        tax_id_number VARCHAR(50),
        commercial_registry VARCHAR(50),
        company_address TEXT,
        company_phone VARCHAR(50),
        notes TEXT
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE discount_companies (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL,
        discount_percent DECIMAL(5,2) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE discount_company_products (
        id INT PRIMARY KEY AUTO_INCREMENT,
        company_id INT NOT NULL,
        product_id INT NOT NULL
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE supplier_promotion_claims (
        id INT PRIMARY KEY AUTO_INCREMENT,
        supplier_id INT NOT NULL,
        promotion_id INT NULL,
        sale_invoice_id INT NULL,
        product_id INT NULL,
        quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
        amount DECIMAL(12,2) NOT NULL DEFAULT 0,
        status VARCHAR(30) NOT NULL DEFAULT 'pending',
        claim_date DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE sales_returns (
        id INT PRIMARY KEY AUTO_INCREMENT,
        return_number VARCHAR(50) NOT NULL UNIQUE,
        original_invoice_id INT NOT NULL,
        store_id INT NOT NULL,
        created_by INT NOT NULL,
        total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
        reason TEXT,
        drawer_id INT NULL,
        status VARCHAR(20) DEFAULT 'completed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (original_invoice_id) REFERENCES invoices(id)
    ) ENGINE=InnoDB;
    """)
    cur.execute("""
    CREATE TABLE return_items (
        id INT PRIMARY KEY AUTO_INCREMENT,
        return_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity DECIMAL(12,3) NOT NULL,
        unit_price DECIMAL(10,2) NOT NULL,
        total_price DECIMAL(12,2) NOT NULL,
        buy_price DECIMAL(10,2) DEFAULT 0,
        FOREIGN KEY (return_id) REFERENCES sales_returns(id) ON DELETE CASCADE
    ) ENGINE=InnoDB;
    """)

    # إدخال بيانات أولية
    cur.execute("INSERT INTO stores (id, store_name) VALUES (1, 'Main Store')")
    cur.execute(
        "INSERT INTO users (id, name, email, store_id) VALUES (1, 'Cashier User', 'cashier@test.com', 1)"
    )
    cur.execute("""
    INSERT INTO products (id, product_code, product_name, buy_price, sell_price, tax_percent)
    VALUES (101, 'P101', 'Test Item 1', 50.0, 100.0, 14.0)
    """)
    cur.execute(
        "INSERT INTO product_inventory (product_id, store_id, quantity_in_stock) VALUES (101, 1, 10.0)"
    )
    cur.execute(
        "INSERT INTO discount_companies (id, name, discount_percent, is_active) VALUES (1, 'Xclusive', 10.0, 1)"
    )

    # توجيه اتصال التطبيق لقاعدة البيانات المؤقتة
    prev_db_name = os.environ.get("POS_DB_NAME", "stocks")
    os.environ["POS_DB_NAME"] = DISPOSABLE_DB_NAME
    DatabaseConnection._instance = None

    yield {
        "conn": conn,
        "cursor": cur,
        "db_name": DISPOSABLE_DB_NAME,
    }

    # تنظيف وتفكيك قاعدة البيانات المؤقتة بعد انتهاء الاختبار
    try:
        try:
            db_inst = getattr(DatabaseConnection, "_instance", None)
            if db_inst is not None:
                db_inst.close()
        except Exception:
            pass
        cur.execute(f"DROP DATABASE IF EXISTS {DISPOSABLE_DB_NAME}")
    except Exception:
        pass
    finally:
        cur.close()
        conn.close()
        os.environ["POS_DB_NAME"] = prev_db_name
        DatabaseConnection._instance = None


def test_real_mysql_checkout_success_commits_all_tables(disposable_mysql):
    """
    اختبار إتمام بيع ناجح على قاعدة بيانات MySQL حقيقية:
    التحقق من تثبيت (Commit) الفاتورة، البنود، خصم المخزون، وحركات الخزينة.
    """
    inv_repo = InvoiceRepository()
    stock_repo = InventoryRepository()
    cart = CashierCartUseCase(stock_repo, inv_repo)
    cart.set_store(1)
    prod = Product(
        id=101,
        product_code="P101",
        product_name="Test Item 1",
        sell_price=100.0,
        tax_percent=14.0,
    )
    cart.add_item(prod, 1)
    cart.set_discount_company({
        "id": 1,
        "name": "Xclusive",
        "discount_percent": 10.0,
        "product_ids": [],
    })

    checkout = CheckoutSaleUseCase(
        invoice_repo=inv_repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=lambda: None,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    inv_num = checkout.execute(
        store_id=1,
        cashier_id=1,
        drawer_id=1,
        payment_method="Cash",
        cash_amount=90.0,
        card_amount=0.0,
    )

    assert inv_num is not None

    cur = disposable_mysql["cursor"]
    cur.execute(f"SELECT COUNT(*) FROM {DISPOSABLE_DB_NAME}.invoices")
    (inv_count,) = cur.fetchone()
    assert inv_count == 1

    cur.execute(
        f"SELECT total_amount, company_discount_amount FROM {DISPOSABLE_DB_NAME}.invoices LIMIT 1"
    )
    total_amt, comp_disc = cur.fetchone()
    assert float(total_amt) == 90.0
    assert float(comp_disc) == 10.0

    cur.execute(
        f"SELECT COUNT(*), discount, total_price FROM {DISPOSABLE_DB_NAME}.invoice_items GROUP BY discount, total_price"
    )
    item_count, disc, tot_price = cur.fetchone()
    assert item_count == 1
    assert float(disc) == 10.0
    assert float(tot_price) == 90.0

    cur.execute(
        f"SELECT quantity_in_stock FROM {DISPOSABLE_DB_NAME}.product_inventory WHERE product_id=101"
    )
    (stock,) = cur.fetchone()
    assert float(stock) == 9.0  # 10 - 1

    cur.execute(f"SELECT COUNT(*) FROM {DISPOSABLE_DB_NAME}.treasury")
    (treasury_count,) = cur.fetchone()
    assert treasury_count == 1

    cur.execute(f"SELECT amount FROM {DISPOSABLE_DB_NAME}.treasury LIMIT 1")
    (treasury_amt,) = cur.fetchone()
    assert float(treasury_amt) == 90.0


@pytest.mark.parametrize(
    "failure_method, failure_msg",
    [
        ("insert_sale_item", "Simulated MySQL item insertion error"),
        (
            "decrease_product_inventory",
            "Simulated MySQL inventory update timeout",
        ),
        (
            "apply_sale_financial_effects",
            "Simulated MySQL treasury constraint violation",
        ),
        ("save_sale_tax_details", "Simulated MySQL tax persistence failure"),
    ],
)
def test_real_mysql_failure_injection_rolls_back_completely(
    disposable_mysql, monkeypatch, failure_method, failure_msg
):
    """
    اختبار حقن الأعطال على جلسة MySQL حقيقية:
    التحقق من أن استدعاء rollback يتراجع عن كافة عمليات INSERT/UPDATE في:
    - invoices
    - invoice_items
    - product_inventory
    - treasury
    ولا يترك أي أثر مالي أو مخزني معلق في MySQL.
    """
    inv_repo = InvoiceRepository()
    stock_repo = InventoryRepository()
    cart = CashierCartUseCase(stock_repo, inv_repo)
    cart.set_store(1)
    prod = Product(
        id=101,
        product_code="P101",
        product_name="Test Item 1",
        sell_price=100.0,
        tax_percent=14.0,
    )
    cart.add_item(prod, 1)
    cart.set_discount_company({
        "id": 1,
        "name": "Xclusive",
        "discount_percent": 10.0,
        "product_ids": [],
    })

    # حقن الفشل في الطريقة المحددة
    def fail_injection(*args, **kwargs):
        raise RuntimeError(failure_msg)

    monkeypatch.setattr(inv_repo, failure_method, fail_injection)

    # تجهيز مزود الضرائب إذا كان الفشل في الضرائب
    from models.invoice import TaxInvoiceDetails

    tax_prov = (
        (lambda: TaxInvoiceDetails(company_name="TaxCorp", tax_id_number="999"))
        if failure_method == "save_sale_tax_details"
        else (lambda: None)
    )

    checkout = CheckoutSaleUseCase(
        invoice_repo=inv_repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=tax_prov,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    with pytest.raises(RuntimeError, match=failure_msg):
        checkout.execute(
            store_id=1,
            cashier_id=1,
            drawer_id=1,
            payment_method="Cash",
            cash_amount=90.0,
            card_amount=0.0,
        )

    # فحص الجداول الفعلية في MySQL للتأكد من التراجع الكامل 100%
    cur = disposable_mysql["cursor"]

    cur.execute(f"SELECT COUNT(*) FROM {DISPOSABLE_DB_NAME}.invoices")
    (inv_count,) = cur.fetchone()
    assert inv_count == 0, "يجب ألا يبقى أي رأس فاتورة بعد التراجع في MySQL"

    cur.execute(f"SELECT COUNT(*) FROM {DISPOSABLE_DB_NAME}.invoice_items")
    (items_count,) = cur.fetchone()
    assert items_count == 0, "يجب ألا يبقى أي بند فاتورة بعد التراجع في MySQL"

    cur.execute(
        f"SELECT quantity_in_stock FROM {DISPOSABLE_DB_NAME}.product_inventory WHERE product_id=101"
    )
    (stock,) = cur.fetchone()
    assert (
        float(stock) == 10.0
    ), "يجب أن يعود رصيد المخزون في MySQL للقيمة الأصلية"

    cur.execute(f"SELECT COUNT(*) FROM {DISPOSABLE_DB_NAME}.treasury")
    (treasury_count,) = cur.fetchone()
    assert treasury_count == 0, "يجب ألا تبقى أي حركة خزينة بعد التراجع في MySQL"


def test_real_mysql_no_ddl_inside_active_checkout_transaction(
    disposable_mysql,
):
    """
    التحقق من عدم تشغيل أي أمر DDL (ALTER TABLE) داخل المعاملة المفتوحة:
    حذف أعمدة شركة الخصم من جدول invoices لمحاكاة قاعدة بيانات قديمة لم يتم ترحيلها عند الإقلاع،
    ثم محاولة إتمام بيع بخصم شركة:
    يجب أن يفشل الكود فوراً باستثناء RuntimeError صريح دون تشغيل ALTER TABLE
    ودون تنفيذ أي Implicit Commit في MySQL.
    """
    inv_repo = InvoiceRepository()
    stock_repo = InventoryRepository()

    # إسقاط الأعمدة بعد تهيئة المستودع لمحاكاة غياب الأعمدة في قاعدة البيانات
    cur = disposable_mysql["cursor"]
    cur.execute(
        f"ALTER TABLE {DISPOSABLE_DB_NAME}.invoices DROP COLUMN discount_company_id"
    )
    cur.execute(
        f"ALTER TABLE {DISPOSABLE_DB_NAME}.invoices DROP COLUMN discount_company_name"
    )
    cur.execute(
        f"ALTER TABLE {DISPOSABLE_DB_NAME}.invoices DROP COLUMN company_discount_amount"
    )
    inv_repo._metadata_cache.clear()

    cart = CashierCartUseCase(stock_repo, inv_repo)
    cart.set_store(1)
    prod = Product(
        id=101,
        product_code="P101",
        product_name="Test Item 1",
        sell_price=100.0,
        tax_percent=14.0,
    )
    cart.add_item(prod, 1)
    cart.set_discount_company({
        "id": 1,
        "name": "Xclusive",
        "discount_percent": 10.0,
        "product_ids": [],
    })

    checkout = CheckoutSaleUseCase(
        invoice_repo=inv_repo,
        totals_calculator=cart.calculate_totals,
        promo_discount_for_product=cart.promo_discount_for_product,
        current_items_provider=lambda: cart.items,
        tax_invoice_provider=lambda: None,
        company_promo_discount_for_product=cart.company_promo_discount_for_product,
    )

    with pytest.raises(RuntimeError) as exc_info:
        checkout.execute(
            store_id=1,
            cashier_id=1,
            drawer_id=1,
            payment_method="Cash",
            cash_amount=90.0,
            card_amount=0.0,
        )

    assert "خارج المعاملة المالية" in str(exc_info.value)

    # التحقق من أن الجدول لم يتم تعديله ولم تُضف الأعمدة بواسطة المعاملة
    cur.execute(
        f"SHOW COLUMNS FROM {DISPOSABLE_DB_NAME}.invoices LIKE 'discount_company_id'"
    )
    assert (
        cur.fetchone() is None
    ), "لا يجوز تشغيل ALTER TABLE لإضافة العمود داخل المعاملة المالية"

    cur.execute(f"SELECT COUNT(*) FROM {DISPOSABLE_DB_NAME}.invoices")
    (inv_count,) = cur.fetchone()
    assert inv_count == 0, "لا يجوز حفظ الفاتورة عند فشل الأعمدة"


def test_real_mysql_migration_008_validation(disposable_mysql):
    """
    التحقق من سلامة الهجرة 008 على قاعدة بيانات حقيقية معزولة:
    1. التحقق من وجود جدول return_items الأصلي بدون invoice_item_id.
    2. إدخال فاتورة تاريخية ومرتجع قديم في return_items بدون invoice_item_id.
    3. تشغيل MigrationRunner لتطبيق هجرة 008.
    4. التحقق من إضافة العمود invoice_item_id كـ INT NULL مع بقائه NULL في السجل القديم.
    5. التحقق من إنشاء الفهرس idx_return_items_invoice_item.
    6. التحقق من تسجيل الهجرة 008 بنجاح في جدول schema_migrations.
    7. اختبار عدم التأثر بالتكرار (Idempotency): تشغيل الهجرة مرة ثانية دون أخطاء.
    """
    cur = disposable_mysql["cursor"]
    db_name = disposable_mysql["db_name"]

    # 1. التحقق من عدم وجود العمود مبدئياً في الجدول التاريخي
    cur.execute(
        f"SELECT COUNT(*) FROM information_schema.columns "
        f"WHERE table_schema = '{db_name}' AND table_name = 'return_items' AND column_name = 'invoice_item_id'"
    )
    (has_col,) = cur.fetchone()
    assert has_col == 0, "العمود يجب ألا يكون موجوداً قبل تشغيل الهجرة"

    # 2. إنشاء فاتورة وسجل مرتجع تاريخي قديم (بدون invoice_item_id)
    cur.execute(
        f"INSERT INTO {db_name}.invoices (id, invoice_number, store_id, cashier_id, total_amount, payment_method) "
        f"VALUES (901, 'INV-HIST-1', 1, 1, 100.0, 'Cash')"
    )
    cur.execute(
        f"INSERT INTO {db_name}.sales_returns (id, return_number, original_invoice_id, store_id, created_by, total_amount) "
        f"VALUES (801, 'RET-HIST-1', 901, 1, 1, 100.0)"
    )
    cur.execute(
        f"INSERT INTO {db_name}.return_items (id, return_id, product_id, quantity, unit_price, total_price) "
        f"VALUES (701, 801, 101, 1, 100.0, 100.0)"
    )

    # تجهيز جدول تتبع الهجرات مع تعليم الهجرات السابقة 001-007 كمنفذة
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {db_name}.schema_migrations ("
        f"id INT AUTO_INCREMENT PRIMARY KEY, "
        f"version VARCHAR(100) NOT NULL UNIQUE, "
        f"name VARCHAR(255) NOT NULL, "
        f"executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        f"checksum VARCHAR(64), "
        f"success BOOLEAN DEFAULT TRUE, "
        f"error_message TEXT) ENGINE=InnoDB"
    )
    for v in ["001", "002", "003", "004", "005", "006", "007"]:
        cur.execute(
            f"INSERT INTO {db_name}.schema_migrations (version, name, success) VALUES (%s, %s, TRUE) "
            f"ON DUPLICATE KEY UPDATE success = TRUE",
            (v, f"{v}_baseline.sql"),
        )

    runner = MigrationRunner(DatabaseConnection())
    success = runner.run_migrations()
    assert success is True, "يجب أن تنجح الهجرة 008 عبر مشغل الهجرات"

    # 4. التحقق من إضافة العمود ومواصفاته (INT, Nullable)
    cur.execute(
        f"SELECT is_nullable, data_type FROM information_schema.columns "
        f"WHERE table_schema = '{db_name}' AND table_name = 'return_items' AND column_name = 'invoice_item_id'"
    )
    col_meta = cur.fetchone()
    assert col_meta is not None, "يجب أن يتم إنشاء العمود invoice_item_id"
    assert col_meta[0] == "YES", "يجب أن يكون العمود قابلاً للقيمة NULL لحماية البيانات التاريخية"
    assert col_meta[1] == "int", "يجب أن يكون نوع العمود INT"

    # التحقق من أن السجل التاريخي القديم احتفظ بـ NULL ولم يتم اختلاق سطر له
    cur.execute(
        f"SELECT invoice_item_id FROM {db_name}.return_items WHERE id = 701"
    )
    (val,) = cur.fetchone()
    assert val is None, "السجل التاريخي القديم يجب أن يبقى invoice_item_id = NULL دون اختلاق روابط غير دقيقة"

    # 5. التحقق من إنشاء الفهرس idx_return_items_invoice_item
    cur.execute(
        f"SELECT COUNT(*) FROM information_schema.statistics "
        f"WHERE table_schema = '{db_name}' AND table_name = 'return_items' AND index_name = 'idx_return_items_invoice_item'"
    )
    (has_idx,) = cur.fetchone()
    assert has_idx > 0, "يجب إنشاء الفهرس idx_return_items_invoice_item"

    # 6. التحقق من تسجيل الهجرة 008 في schema_migrations
    cur.execute(
        f"SELECT success FROM {db_name}.schema_migrations WHERE version = '008'"
    )
    row = cur.fetchone()
    assert row is not None and row[0] == 1, "يجب تسجيل نجاح الهجرة 008 في جدول الهجرات"

    # 7. اختبار عدم التأثر بالتكرار (Idempotency)
    second_run = runner.run_migrations()
    assert second_run is True, "إعادة تشغيل الهجرات يجب أن تتخطى الهجرة المطبقة مسبقاً بنجاح دون أي خطأ"
    runner.db.close()


def test_real_mysql_concurrent_returns_serialize_and_prevent_double_refund(disposable_mysql):
    """
    التحقق من قفل التزامن ومنع استرداد نفس الكمية مرتين في بيئة MySQL InnoDB الحقيقية:
    1. تطبيق الهجرة 008.
    2. إدخال فاتورة حقيقية تحتوي على سطر بكمية 2 وإجمالي 200.0 ج.م، ورصيد المخزون 8.
    3. إطلاق خيطين متزامنين يحاول كل منهما إرجاع الكمية 2 بالكامل في نفس اللحظة عبر حاجز متزامن.
    4. بفضل قفل SELECT ... FOR UPDATE على الفاتورة، تتسلسل العمليتان (Serialization):
       - ينجح خيط واحد فقط في إتمام المرتجع واسترداد 200.0 ج.م.
       - يفشل الخيط الآخر فور فك القفل وقراءة الرصيد المتبقي (0 متاح) ويتم التراجع الكامل.
    5. التحقق من قواعد البيانات في MySQL:
       - sales_returns: حركة مرتجع واحدة فقط.
       - return_items: كمية مسترجعة 2 فقط (وليس 4).
       - product_inventory: المخزون عاد إلى 10 بالضبط (8 + 2).
       - treasury: حركة صرف واحدة بقيمة 200.0 ج.م فقط (وليس 400.0).
    """
    cur = disposable_mysql["cursor"]
    db_name = disposable_mysql["db_name"]

    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {db_name}.schema_migrations ("
        f"id INT AUTO_INCREMENT PRIMARY KEY, "
        f"version VARCHAR(100) NOT NULL UNIQUE, "
        f"name VARCHAR(255) NOT NULL, "
        f"executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        f"checksum VARCHAR(64), "
        f"success BOOLEAN DEFAULT TRUE, "
        f"error_message TEXT) ENGINE=InnoDB"
    )
    for v in ["001", "002", "003", "004", "005", "006", "007"]:
        cur.execute(
            f"INSERT INTO {db_name}.schema_migrations (version, name, success) VALUES (%s, %s, TRUE) "
            f"ON DUPLICATE KEY UPDATE success = TRUE",
            (v, f"{v}_baseline.sql"),
        )
    runner = MigrationRunner(DatabaseConnection())
    assert runner.run_migrations() is True

    # إنشاء فاتورة وبند فاتورة في MySQL
    cur.execute(
        f"INSERT INTO {db_name}.invoices "
        f"(id, invoice_number, store_id, cashier_id, total_amount, paid_amount, remaining_amount, cash_amount, payment_method, status) "
        f"VALUES (910, 'INV-CONCUR-1', 1, 1, 200.0, 200.0, 0.0, 200.0, 'Cash', 'Completed')"
    )
    cur.execute(
        f"INSERT INTO {db_name}.invoice_items "
        f"(id, invoice_id, product_id, quantity, unit_price, discount, total_price, buy_price) "
        f"VALUES (810, 910, 101, 2.0, 100.0, 0.0, 200.0, 50.0)"
    )
    cur.execute(
        f"UPDATE {db_name}.product_inventory SET quantity_in_stock = 8.0 WHERE product_id = 101 AND store_id = 1"
    )

    results = {}
    barrier = threading.Barrier(2)

    def worker(worker_id):
        barrier.wait()
        try:
            repo = ReturnsRepository()
            use_case = ProcessReturnUseCase(repo)
            res = use_case.execute(
                invoice_id=910,
                items=[{"invoice_item_id": 810, "quantity": 2}],
                reason=f"Concurrent return from worker {worker_id}",
                user_id=1,
                store_id=1,
            )
            results[worker_id] = (res, use_case.last_error)
        finally:
            db_conn = getattr(getattr(DatabaseConnection(), "_local", None), "conn", None)
            if db_conn and db_conn.is_connected():
                db_conn.close()

    t1 = threading.Thread(target=worker, args=(1,))
    t2 = threading.Thread(target=worker, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [res for res, err in results.values() if res is not None]
    failures = [err for res, err in results.values() if res is None]

    assert len(successes) == 1, f"يجب أن ينجح خيط واحد فقط من أصل اثنين، النتائج: {results}"
    assert len(failures) == 1, f"يجب أن يفشل الخيط الآخر بسبب نفاد الكمية المتاحة، النتائج: {results}"
    assert "كمية المرتجع غير صحيحة" in failures[0]

    # فحص القيود في MySQL للتأكد من عدم وجود أي تكرار
    cur.execute(f"SELECT COUNT(*) FROM {db_name}.sales_returns WHERE original_invoice_id = 910")
    (sr_count,) = cur.fetchone()
    assert sr_count == 1, "يجب أن يُنشأ رأس مرتجع واحد فقط في MySQL"

    cur.execute(
        f"SELECT SUM(quantity), SUM(total_price) FROM {db_name}.return_items "
        f"WHERE invoice_item_id = 810"
    )
    sum_qty, sum_total = cur.fetchone()
    assert float(sum_qty) == 2.0, "إجمالي الكمية المسترجعة يجب أن يكون 2 فقط"
    assert float(sum_total) == 200.0, "إجمالي المبلغ المسترجع يجب أن يكون 200.0 ج.م"

    cur.execute(
        f"SELECT quantity_in_stock FROM {db_name}.product_inventory WHERE product_id = 101 AND store_id = 1"
    )
    (final_stock,) = cur.fetchone()
    assert float(final_stock) == 10.0, "المخزون يجب أن يعود إلى 10 بالضبط (8 + 2) دون زيادة مزدوجة"

    cur.execute(
        f"SELECT COUNT(*), SUM(amount) FROM {db_name}.treasury WHERE source_type = 'Return'"
    )
    tr_count, tr_amount = cur.fetchone()
    assert tr_count == 1, "يجب أن تسجل حركة خزينة واحدة فقط للاسترداد النقدي"
    assert float(tr_amount) == 200.0, "قيمة حركة الخزينة يجب أن تكون 200.0 ج.م فقط"


def test_real_mysql_line_level_return_atomicity_and_duplicate_products(disposable_mysql):
    """
    التحقق من إرجاع الصنف المكرر في سطرين مختلفين بأسعار وخصومات متفاوتة في MySQL الحقيقي:
    - السطر 821: 1 قطعة بسعر 50 (خصم 50%)
    - السطر 822: 1 قطعة بسعر 100 (خصم 0%)
    إرجاع السطر 821 يسترد 50.0 ج.م ويترك السطر 822 متاحاً بالكامل (100.0 ج.م).
    إرجاع السطر 822 يسترد 100.0 ج.م.
    """
    cur = disposable_mysql["cursor"]
    db_name = disposable_mysql["db_name"]

    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {db_name}.schema_migrations ("
        f"id INT AUTO_INCREMENT PRIMARY KEY, "
        f"version VARCHAR(100) NOT NULL UNIQUE, "
        f"name VARCHAR(255) NOT NULL, "
        f"executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        f"checksum VARCHAR(64), "
        f"success BOOLEAN DEFAULT TRUE, "
        f"error_message TEXT) ENGINE=InnoDB"
    )
    for v in ["001", "002", "003", "004", "005", "006", "007"]:
        cur.execute(
            f"INSERT INTO {db_name}.schema_migrations (version, name, success) VALUES (%s, %s, TRUE) "
            f"ON DUPLICATE KEY UPDATE success = TRUE",
            (v, f"{v}_baseline.sql"),
        )
    runner = MigrationRunner(DatabaseConnection())
    assert runner.run_migrations() is True

    cur.execute(
        f"INSERT INTO {db_name}.invoices "
        f"(id, invoice_number, store_id, cashier_id, total_amount, paid_amount, remaining_amount, cash_amount, payment_method, status) "
        f"VALUES (920, 'INV-DUP-1', 1, 1, 150.0, 150.0, 0.0, 150.0, 'Cash', 'Completed')"
    )
    cur.execute(
        f"INSERT INTO {db_name}.invoice_items "
        f"(id, invoice_id, product_id, quantity, unit_price, discount, total_price, buy_price) "
        f"VALUES (821, 920, 101, 1.0, 100.0, 50.0, 50.0, 50.0)"
    )
    cur.execute(
        f"INSERT INTO {db_name}.invoice_items "
        f"(id, invoice_id, product_id, quantity, unit_price, discount, total_price, buy_price) "
        f"VALUES (822, 920, 101, 1.0, 100.0, 0.0, 100.0, 50.0)"
    )

    repo = ReturnsRepository()
    use_case = ProcessReturnUseCase(repo)

    # 1. إرجاع السطر الأول المخفض فقط
    ret1 = use_case.execute(
        invoice_id=920,
        items=[{"invoice_item_id": 821, "quantity": 1}],
        reason="إرجاع السطر المخفض",
        user_id=1,
        store_id=1,
    )
    assert ret1 is not None
    assert ret1["total_amount"] == 50.0

    # 2. إرجاع السطر الثاني غير المخفض
    ret2 = use_case.execute(
        invoice_id=920,
        items=[{"invoice_item_id": 822, "quantity": 1}],
        reason="إرجاع السطر غير المخفض",
        user_id=1,
        store_id=1,
    )
    assert ret2 is not None
    assert ret2["total_amount"] == 100.0

    # التحقق من أن إجمالي المرتجعات 150.0 ج.م مطابقة تماماً للمدفوع
    assert ret1["total_amount"] + ret2["total_amount"] == 150.0

