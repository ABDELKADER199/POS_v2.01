"""
Product Repository - مستودع المنتجات
جميع عمليات CRUD المتعلقة بالمنتجات
"""
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from repositories.base_repo import BaseRepository
from models.product import Product

logger = logging.getLogger(__name__)


class ProductRepository(BaseRepository):
    """مستودع عمليات المنتجات"""

    def __init__(self):
        super().__init__()
        self.ensure_product_columns()

    def commit(self):
        self._commit()

    def rollback(self):
        self._rollback()

    def _columns(self, table_name: str) -> set:
        return {row["Field"] for row in self._fetch_all(f"SHOW COLUMNS FROM {table_name}")}

    def ensure_product_columns(self):
        try:
            columns = self._columns("products")
            if "image_path" not in columns:
                self._execute("ALTER TABLE products ADD COLUMN image_path VARCHAR(255) NULL")
            if "import_status" not in columns:
                self._execute("ALTER TABLE products ADD COLUMN import_status VARCHAR(30) NOT NULL DEFAULT 'ready'")
            if "import_notes" not in columns:
                self._execute("ALTER TABLE products ADD COLUMN import_notes VARCHAR(255) NULL")
            self._commit()
        except Exception as e:
            self._rollback()
            logger.error(f"Error ensuring product columns: {e}")

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """جلب منتج بالمعرف"""
        row = self._fetch_one("SELECT * FROM products WHERE id = %s", (product_id,))
        return Product.from_dict(row) if row else None

    def get_by_code(self, product_code: str) -> Optional[Product]:
        """جلب منتج بالكود"""
        row = self._fetch_one(
            "SELECT * FROM products WHERE product_code = %s AND is_active = TRUE",
            (product_code,)
        )
        return Product.from_dict(row) if row else None

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        """جلب منتج بالباركود"""
        row = self._fetch_one(
            "SELECT * FROM products WHERE barcode = %s AND is_active = TRUE",
            (barcode,)
        )
        return Product.from_dict(row) if row else None

    def search(self, term: str, store_id: int = None,
               category_id: int = None, supplier_id: int = None,
               limit: int = 50, offset: int = 0,
               column_filters: Dict = None) -> List[Product]:
        """بحث في المنتجات"""
        query = "SELECT * FROM products WHERE is_active = TRUE"
        params = []

        if term:
            query += " AND (product_name LIKE %s OR product_code LIKE %s OR barcode LIKE %s)"
            like = f"%{term}%"
            params.extend([like, like, like])

        if category_id:
            query += " AND category_id = %s"
            params.append(category_id)

        if supplier_id:
            query += " AND supplier_id = %s"
            params.append(supplier_id)

        query, params = self._apply_column_filters(query, params, column_filters)

        order_by = self._order_clause(column_filters)
        query += f" ORDER BY {order_by} LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        rows = self._fetch_all(query, tuple(params))
        return [Product.from_dict(r) for r in rows]

    def count(self, term: str = None, category_id: int = None, supplier_id: int = None,
              column_filters: Dict = None) -> int:
        """عدد المنتجات"""
        query = "SELECT COUNT(*) as cnt FROM products WHERE is_active = TRUE"
        params = []

        if term:
            query += " AND (product_name LIKE %s OR product_code LIKE %s OR barcode LIKE %s)"
            like = f"%{term}%"
            params.extend([like, like, like])
        if category_id:
            query += " AND category_id = %s"
            params.append(category_id)
        if supplier_id:
            query += " AND supplier_id = %s"
            params.append(supplier_id)

        query, params = self._apply_column_filters(query, params, column_filters)

        row = self._fetch_one(query, tuple(params))
        return row['cnt'] if row else 0

    def _apply_column_filters(self, query: str, params: list, filters: Dict = None) -> tuple[str, list]:
        filters = filters or {}
        code = (filters.get("code") or "").strip()
        name = (filters.get("name") or "").strip()
        unit = (filters.get("unit") or "").strip()
        status = (filters.get("status") or "").strip()
        min_buy = filters.get("min_buy")
        max_buy = filters.get("max_buy")
        min_sell = filters.get("min_sell")
        max_sell = filters.get("max_sell")

        if code:
            query += " AND (product_code LIKE %s OR barcode LIKE %s)"
            like = f"%{code}%"
            params.extend([like, like])
        if name:
            query += " AND product_name LIKE %s"
            params.append(f"%{name}%")
        if unit:
            query += " AND unit LIKE %s"
            params.append(f"%{unit}%")
        if status:
            query += " AND COALESCE(import_status, 'ready') = %s"
            params.append(status)
        if min_buy is not None:
            query += " AND buy_price >= %s"
            params.append(float(min_buy))
        if max_buy is not None:
            query += " AND buy_price <= %s"
            params.append(float(max_buy))
        if min_sell is not None:
            query += " AND sell_price >= %s"
            params.append(float(min_sell))
        if max_sell is not None:
            query += " AND sell_price <= %s"
            params.append(float(max_sell))
        return query, params

    def _order_clause(self, filters: Dict = None) -> str:
        filters = filters or {}
        sort_by = (filters.get("sort_by") or "").strip()
        direction = (filters.get("sort_direction") or "").strip().lower()
        direction_sql = "DESC" if direction == "desc" else "ASC"
        allowed = {
            "sell_price": "sell_price",
        }
        column = allowed.get(sort_by)
        if not column:
            return "product_name"
        return f"{column} {direction_sql}, product_name"

    def insert_product(self, product: Product, store_id: int = None) -> int:
        if not store_id:
            raise ValueError("يجب تحديد الفرع قبل إضافة المنتج")
        store_id = int(store_id)
        columns = [
            "product_code", "product_name", "category_id", "buy_price",
            "sell_price", "supplier_id", "unit", "barcode", "tax_percent",
            "image_path", "import_status", "import_notes", "is_active",
        ]
        values = [
            product.product_code, product.product_name, product.category_id,
            product.buy_price, product.sell_price, product.supplier_id,
            product.unit, product.barcode or product.product_code,
            product.tax_percent, product.image_path,
            product.import_status, product.import_notes, True,
        ]
        if "store_id" in self._columns("products"):
            columns.insert(3, "store_id")
            values.insert(3, store_id)
        placeholders = ", ".join(["%s"] * len(values))
        self._execute(
            f"INSERT INTO products ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )
        return self._last_id

    def set_initial_stock(self, product_id: int, store_id: int, initial_stock: int):
        self._execute("""
            INSERT INTO product_inventory (product_id, store_id, quantity_in_stock)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity_in_stock = quantity_in_stock + VALUES(quantity_in_stock)
        """, (product_id, store_id, initial_stock))

    def update_product_record(self, product: Product):
        self._execute("""
            UPDATE products SET
                product_code = %s, product_name = %s, category_id = %s,
                buy_price = %s, sell_price = %s, supplier_id = %s,
                unit = %s, barcode = %s, tax_percent = %s, image_path = %s,
                import_status = %s, import_notes = %s
            WHERE id = %s
        """, (
            product.product_code, product.product_name, product.category_id,
            product.buy_price, product.sell_price, product.supplier_id,
            product.unit, product.barcode or product.product_code,
            product.tax_percent, product.image_path,
            product.import_status, product.import_notes, product.id
        ))

    def soft_delete_product(self, product_id: int):
        self._execute("UPDATE products SET is_active = FALSE WHERE id = %s", (product_id,))

    def save_product_image(self, source_path: str, product_code: str) -> str:
        if not source_path or not os.path.exists(source_path):
            raise ValueError("ملف الصورة غير موجود")
        ext = Path(source_path).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            raise ValueError("صيغة الصورة غير مدعومة")
        image_dir = Path(os.getcwd()) / "assets" / "product_images"
        image_dir.mkdir(parents=True, exist_ok=True)
        safe_code = re.sub(r"[^\w\-.]+", "_", product_code or "product", flags=re.UNICODE).strip("_")
        target = image_dir / f"{safe_code}{'.jpg' if ext == '.jpeg' else ext}"
        shutil.copy2(source_path, target)
        return str(target)

    def update_zero_costs_from_margin(self, margin_percent: float = 25.0) -> int:
        """تصحيح سعر شراء المنتجات التي لا تحتوي على تكلفة."""
        factor = 1.0 - (margin_percent / 100.0)
        self._execute("""
                UPDATE products
                SET buy_price = sell_price * %s
                WHERE (buy_price IS NULL OR buy_price = 0)
                  AND sell_price > 0
                  AND is_active = TRUE
            """, (factor,))
        return self._affected_rows

    def get_categories(self) -> List[Dict]:
        """جلب الفئات النشطة"""
        return self._fetch_all("""
            SELECT id, category_name
            FROM categories
            WHERE is_active = TRUE
            ORDER BY category_name
        """)

    def _legacy_add_category(self, category_name: str) -> int:
        """إضافة فئة جديدة"""
        try:
            self._execute(
                "INSERT INTO categories (category_name, is_active) VALUES (%s, TRUE)",
                (category_name,)
            )
            category_id = self._last_id
            self._commit()
            return category_id
        except Exception as e:
            self._rollback()
            logger.error(f"Error adding category: {e}")
            raise

    def _legacy_update_category(self, category_id: int, category_name: str) -> bool:
        """تعديل اسم فئة"""
        try:
            self._execute(
                "UPDATE categories SET category_name = %s WHERE id = %s",
                (category_name, category_id)
            )
            self._commit()
            return True
        except Exception as e:
            self._rollback()
            logger.error(f"Error updating category {category_id}: {e}")
            return False

    def _legacy_delete_category(self, category_id: int) -> bool:
        """تعطيل فئة بدون كسر المنتجات المرتبطة بها"""
        try:
            self._execute(
                "UPDATE categories SET is_active = FALSE WHERE id = %s",
                (category_id,)
            )
            self._commit()
            return True
        except Exception as e:
            self._rollback()
            logger.error(f"Error deleting category {category_id}: {e}")
            return False

    def insert_category(self, category_name: str) -> int:
        self._execute(
            "INSERT INTO categories (category_name, is_active) VALUES (%s, TRUE)",
            (category_name,)
        )
        return self._last_id

    def update_category_record(self, category_id: int, category_name: str) -> None:
        self._execute(
            "UPDATE categories SET category_name = %s WHERE id = %s",
            (category_name, category_id)
        )

    def soft_delete_category(self, category_id: int) -> None:
        self._execute(
            "UPDATE categories SET is_active = FALSE WHERE id = %s",
            (category_id,)
        )

    def get_or_create_category(self, category_name: str) -> int:
        category_name = (category_name or '').strip() or 'غير مصنف'
        row = self._fetch_one(
            "SELECT id FROM categories WHERE category_name = %s LIMIT 1",
            (category_name,),
        )
        if row:
            return row["id"]
        return self.insert_category(category_name)

    def next_numeric_internal_code(self) -> str:
        row = self._fetch_one("""
            SELECT MAX(CAST(product_code AS UNSIGNED)) AS max_code
            FROM products
            WHERE product_code REGEXP '^90[0-9]{10}$'
        """)
        max_code = int(row.get("max_code") or 900000000000) if row else 900000000000
        return str(max_code + 1).zfill(12)

    def code_exists(self, code: str) -> bool:
        row = self._fetch_one(
            "SELECT id FROM products WHERE product_code = %s OR barcode = %s LIMIT 1",
            (code, code),
        )
        return bool(row)

    def name_exists(self, name: str) -> bool:
        row = self._fetch_one(
            "SELECT id FROM products WHERE product_name = %s AND is_active = TRUE LIMIT 1",
            (name,),
        )
        return bool(row)

    def get_existing_codes_and_names(self) -> tuple[set, set]:
        rows = self._fetch_all("""
            SELECT product_code, barcode, product_name
            FROM products
            WHERE is_active = TRUE
        """)
        codes = set()
        names = set()
        for row in rows:
            if row.get("product_code"):
                codes.add(str(row["product_code"]))
            if row.get("barcode"):
                codes.add(str(row["barcode"]))
            if row.get("product_name"):
                names.add(str(row["product_name"]).strip())
        return codes, names

    def get_category_map(self) -> Dict[str, int]:
        rows = self._fetch_all("SELECT id, category_name FROM categories")
        return {str(row["category_name"]).strip(): row["id"] for row in rows if row.get("category_name")}

    def get_or_create_categories(self, category_names: list[str]) -> Dict[str, int]:
        result = self.get_category_map()
        missing = []
        seen = set(result)
        for name in category_names:
            category_name = (name or '').strip() or 'غير مصنف'
            if category_name not in seen:
                missing.append((category_name, True))
                seen.add(category_name)
        if missing:
            try:
                self._execute_many(
                    "INSERT INTO categories (category_name, is_active) VALUES (%s, %s)",
                    missing,
                )
                self._commit()
            except Exception as e:
                self._rollback()
                logger.error(f"Error bulk creating categories: {e}")
                raise
            result = self.get_category_map()
        return result

    def bulk_create(self, products: list[Product], stock_by_code: dict[str, int],
                    store_id: int = None, chunk_size: int = 1000) -> int:
        if not products:
            return 0
        if not store_id:
            raise ValueError("يجب تحديد الفرع قبل استيراد المنتجات")
        store_id = int(store_id)
        product_columns = [
            "product_code", "product_name", "category_id", "buy_price",
            "sell_price", "supplier_id", "unit", "barcode", "tax_percent",
            "image_path", "import_status", "import_notes", "is_active",
        ]
        include_store_id = "store_id" in self._columns("products")
        if include_store_id:
            product_columns.insert(3, "store_id")

        product_rows = [
            tuple(
                [
                product.product_code,
                product.product_name,
                product.category_id,
                *([store_id] if include_store_id else []),
                product.buy_price,
                product.sell_price,
                product.supplier_id,
                product.unit,
                product.barcode or product.product_code,
                product.tax_percent,
                product.image_path,
                product.import_status,
                product.import_notes,
                True,
                ]
            )
            for product in products
        ]
        try:
            placeholders = ", ".join(["%s"] * len(product_columns))
            insert_query = f"""
                INSERT INTO products ({', '.join(product_columns)})
                VALUES ({placeholders})
            """
            for start in range(0, len(product_rows), chunk_size):
                self._execute_many(insert_query, product_rows[start:start + chunk_size])

            codes = [product.product_code for product in products]
            inventory_rows = []
            for start in range(0, len(codes), chunk_size):
                chunk = codes[start:start + chunk_size]
                placeholders = ",".join(["%s"] * len(chunk))
                id_rows = self._fetch_all(
                    f"SELECT id, product_code FROM products WHERE product_code IN ({placeholders})",
                    tuple(chunk),
                )
                for row in id_rows:
                    quantity = int(stock_by_code.get(str(row["product_code"]), 0) or 0)
                    inventory_rows.append((row["id"], store_id, quantity))

            for start in range(0, len(inventory_rows), chunk_size):
                self._execute_many("""
                    INSERT INTO product_inventory (product_id, store_id, quantity_in_stock)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE quantity_in_stock = quantity_in_stock + VALUES(quantity_in_stock)
                """, inventory_rows[start:start + chunk_size])

            self._commit()
            return len(products)
        except Exception as e:
            self._rollback()
            logger.error(f"Error bulk creating products: {e}")
            raise

    def get_suppliers(self, active_only: bool = True) -> List[Dict]:
        """جلب الموردين"""
        query = "SELECT id, name FROM suppliers"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        return self._fetch_all(query)

    def get_cross_branch_stock(self, search_term: str) -> Dict:
        """جلب المنتج مع مخزونه بجميع الفروع"""
        row = self._fetch_one("""
            SELECT p.*, pi.quantity_in_stock, pi.store_id
            FROM products p
            LEFT JOIN product_inventory pi ON p.id = pi.product_id
            WHERE (p.product_code = %s OR p.barcode = %s) AND p.is_active = TRUE
            LIMIT 1
        """, (search_term, search_term))
        if not row:
            return {}
        return row
