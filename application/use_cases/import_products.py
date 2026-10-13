import csv
from pathlib import Path
from time import perf_counter
from typing import Dict, List

from application.ports.product_import_port import ProductImportRepositoryPort
from models.product import Product


class ProductImportUseCase:
    def __init__(self, product_repo: ProductImportRepositoryPort):
        self.product_repo = product_repo

    def product_import_state(self, sell_price, buy_price, notes: str = None) -> tuple[str, str]:
        sell_price = float(sell_price or 0)
        buy_price = float(buy_price or 0)
        note_parts = [part for part in [notes] if part]
        if sell_price <= 0:
            note_parts.append("ناقص سعر بيع")
            return "needs_pricing", " - ".join(dict.fromkeys(note_parts))
        if buy_price <= 0:
            note_parts.append("ناقص تكلفة")
            return "needs_cost", " - ".join(dict.fromkeys(note_parts))
        return "ready", notes or ""

    def preview_import_file(self, file_path: str) -> Dict:
        raw_rows = self._read_import_rows(file_path)
        preview = []
        next_code = int(self.product_repo.next_numeric_internal_code())
        existing_codes, existing_names = self.product_repo.get_existing_codes_and_names()
        used_codes = set()
        used_names = set()

        for index, raw in enumerate(raw_rows, start=1):
            name = str(self._pick(
                raw, "اسم المنتج", "الاسم", "name", "product_name", "product name"
            ) or "").strip()
            supplied_code = self._pick(
                raw, "الكود", "كود", "barcode", "باركود", "الباركود", "product_code", "code"
            )
            code = self._clean_numeric_code(supplied_code)
            generated_code = False
            notes = []

            if not name:
                preview.append({
                    "row_number": index + 1,
                    "product_code": "",
                    "product_name": "",
                    "sell_price": 0,
                    "buy_price": 0,
                    "unit": "قطعة",
                    "category_name": "غير مصنف",
                    "initial_stock": 0,
                    "tax_percent": 0,
                    "import_status": "invalid",
                    "import_notes": "اسم المنتج مطلوب",
                    "importable": False,
                    "generated_code": False,
                })
                continue

            if not code:
                while str(next_code) in used_codes or str(next_code) in existing_codes:
                    next_code += 1
                code = str(next_code).zfill(12)
                next_code += 1
                generated_code = True
                notes.append("تم توليد كود رقمي")
            elif code in existing_codes or code in used_codes:
                notes.append("كود مكرر")

            if name in existing_names or name in used_names:
                notes.append("اسم مكرر")

            buy_price = self._to_float(self._pick(raw, "سعر الشراء", "تكلفة", "التكلفة", "buy_price", "cost"))
            sell_price = self._to_float(self._pick(raw, "سعر البيع", "السعر", "sell_price", "price"))
            import_status, state_notes = self.product_import_state(sell_price, buy_price)
            if state_notes:
                notes.extend([part for part in state_notes.split(" - ") if part])

            category_name = str(self._pick(raw, "الفئة", "الفئه", "category", "category_name") or "غير مصنف").strip() or "غير مصنف"
            unit = str(self._pick(raw, "الوحدة", "الوحده", "unit") or "قطعة").strip() or "قطعة"
            initial_stock = self._to_int(self._pick(raw, "المخزون", "الكمية", "quantity", "stock"))
            tax_percent = self._to_float(self._pick(raw, "الضريبة", "الضريبه", "tax", "tax_percent"))
            importable = not any(note in {"كود مكرر", "اسم مكرر"} for note in notes)

            preview.append({
                "row_number": index + 1,
                "product_code": code,
                "barcode": code,
                "product_name": name,
                "category_name": category_name,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "unit": unit,
                "initial_stock": initial_stock,
                "tax_percent": tax_percent,
                "import_status": import_status if importable else "duplicate",
                "import_notes": " - ".join(dict.fromkeys(notes)),
                "importable": importable,
                "generated_code": generated_code,
            })
            used_codes.add(code)
            used_names.add(name)

        return {
            "processed": len(raw_rows),
            "rows": preview,
            "ready": sum(1 for row in preview if row["import_status"] == "ready"),
            "needs_pricing": sum(1 for row in preview if row["import_status"] == "needs_pricing"),
            "needs_cost": sum(1 for row in preview if row["import_status"] == "needs_cost"),
            "blocked": sum(1 for row in preview if not row["importable"]),
        }

    def commit_import_preview(self, rows: List[Dict], store_id: int, include_incomplete: bool = True) -> Dict:
        results = {"processed": 0, "valid": 0, "errors": 0, "skipped": 0, "error_samples": []}
        category_names = [
            row.get("category_name") or "غير مصنف"
            for row in rows
            if row.get("importable") and (include_incomplete or row.get("import_status") == "ready")
        ]
        category_map = self.product_repo.get_or_create_categories(category_names)
        existing_codes, _existing_names = self.product_repo.get_existing_codes_and_names()
        products = []
        stock_by_code = {}

        for row in rows:
            results["processed"] += 1
            if not row.get("importable"):
                results["skipped"] += 1
                continue
            if not include_incomplete and row.get("import_status") != "ready":
                results["skipped"] += 1
                continue

            try:
                product_code = row.get("product_code") or self.product_repo.next_numeric_internal_code()
                while product_code in existing_codes:
                    if str(product_code).isdigit() and str(product_code).startswith("90"):
                        product_code = str(int(product_code) + 1).zfill(12)
                    else:
                        raise ValueError("كود مكرر")
                existing_codes.add(product_code)
                category_name = row.get("category_name") or "غير مصنف"
                import_status, import_notes = self.product_import_state(
                    row.get("sell_price") or 0,
                    row.get("buy_price") or 0,
                    row.get("import_notes") or "",
                )
                products.append(Product(
                    product_code=product_code,
                    barcode=product_code,
                    product_name=row.get("product_name", ""),
                    category_id=category_map.get(category_name) or category_map.get("غير مصنف") or 1,
                    buy_price=float(row.get("buy_price") or 0),
                    sell_price=float(row.get("sell_price") or 0),
                    unit=row.get("unit") or "قطعة",
                    tax_percent=float(row.get("tax_percent") or 0),
                    import_status=row.get("import_status") or import_status,
                    import_notes=import_notes,
                ))
                stock_by_code[product_code] = int(row.get("initial_stock") or 0)
            except Exception as row_err:
                results["errors"] += 1
                if len(results["error_samples"]) < 5:
                    results["error_samples"].append(f"Row {row.get('row_number')}: {row_err}")

        try:
            results["valid"] = self.product_repo.bulk_create(products, stock_by_code, store_id)
        except Exception as bulk_err:
            results["errors"] += len(products)
            if len(results["error_samples"]) < 5:
                results["error_samples"].append(str(bulk_err))
        return results

    def import_from_excel(self, file_path: str, store_id: int) -> Dict:
        started_at = perf_counter()
        preview = self.preview_import_file(file_path)
        results = self.commit_import_preview(preview["rows"], store_id, include_incomplete=True)
        results.update({
            "ready": preview.get("ready", 0),
            "needs_pricing": preview.get("needs_pricing", 0),
            "needs_cost": preview.get("needs_cost", 0),
            "blocked": preview.get("blocked", 0),
        })
        results["elapsed"] = round(perf_counter() - started_at, 1)
        return results

    def _clean_numeric_code(self, value) -> str:
        text = str(value or "").strip()
        if text.endswith(".0"):
            text = text[:-2]
        return text if text.isdigit() else ""

    def _to_float(self, value, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip().replace(",", "."))
        except ValueError:
            return default

    def _to_int(self, value, default: int = 0) -> int:
        try:
            return int(float(value or default))
        except (TypeError, ValueError):
            return default

    def _header_key(self, value) -> str:
        text = str(value or "").strip().lower()
        for old, new in {
            " ": "", "_": "", "-": "", ":": "", "/": "",
            "أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه",
        }.items():
            text = text.replace(old, new)
        return text

    def _pick(self, row: dict, *keys, default=""):
        for key in keys:
            normalized = self._header_key(key)
            if normalized in row and row[normalized] not in (None, ""):
                return row[normalized]
        return default

    def _read_import_rows(self, file_path: str) -> List[Dict]:
        suffix = Path(file_path).suffix.lower()
        if suffix in {".xlsx", ".xlsm"}:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            ws = wb.active
            raw_rows = list(ws.iter_rows(values_only=True))
            wb.close()
        elif suffix == ".csv":
            with open(file_path, "r", encoding="utf-8-sig", newline="") as handle:
                raw_rows = list(csv.reader(handle))
        else:
            raise ValueError("صيغة الملف غير مدعومة")

        if not raw_rows:
            return []

        headers = [self._header_key(cell) for cell in raw_rows[0]]
        known_headers = {
            "الكود", "كود", "barcode", "باركود", "الباركود",
            "الاسم", "اسمالمنتج", "productname", "name",
            "سعرالبيع", "sellprice", "price",
        }
        has_header = any(header in known_headers for header in headers)
        if has_header:
            data_rows = raw_rows[1:]
        else:
            data_rows = raw_rows
            headers = [
                "الكود", "الاسم", "الفئه", "سعرالشراء", "سعرالبيع",
                "الوحده", "المورد", "المخزون", "الضريبه",
            ]

        rows = []
        for raw_row in data_rows:
            normalized_row = {}
            for index, header in enumerate(headers):
                if header:
                    normalized_row[header] = raw_row[index] if index < len(raw_row) else None
            rows.append(normalized_row)
        return rows
