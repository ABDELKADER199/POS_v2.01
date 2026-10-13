"""
Promotion Catalog Service - إنشاء مجلة عروض PDF احترافية برسوم مباشرة.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from PIL import Image, ImageOps
from PyQt6.QtCore import QMarginsF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QTextDocument,
    QTextOption,
)
from ui.styles import COLORS

from application.errors import PromotionCatalogError


class PromotionCatalogService:
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    PAGE_WIDTH = 595
    PAGE_HEIGHT = 842
    MARGIN = 30

    def __init__(self, repo):
        self.repo = repo
        self.image_dir = Path(os.getcwd()) / "assets" / "product_images"
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self._http_cache = {}

    def create_pdf(
        self, download_missing_images: bool = True, refresh_images: bool = True
    ) -> Dict:
        products = self.repo.get_active_promotion_catalog_products()
        if not products:
            raise PromotionCatalogError("لا توجد عروض نشطة حاليًا لإنشاء المجلة")

        products = self._deduplicate_products(products)
        prepared_products = []
        for product in products:
            item = dict(product)
            image_path = self._resolve_product_image(
                item, download_missing_images, refresh_images
            )
            item["resolved_image_path"] = image_path
            prepared_products.append(item)

        prefix = f"مجلة_العروض_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pdf_path = self._save_catalog_pdf(prepared_products, prefix)
        if not pdf_path:
            raise PromotionCatalogError("تعذر إنشاء ملف PDF")

        image_count = sum(
            1 for product in prepared_products if product.get("resolved_image_path")
        )
        return {
            "pdf_path": pdf_path,
            "count": len(prepared_products),
            "image_count": image_count,
            "missing_images": len(prepared_products) - image_count,
        }

    def _resolve_product_image(
        self, product: Dict, download_missing_images: bool, refresh_images: bool = False
    ) -> Optional[str]:
        existing = (product.get("image_path") or "").strip()
        local_existing = self._local_existing_image(existing)
        if local_existing and not self._is_generated_placeholder(local_existing):
            return local_existing

        if existing.startswith(("http://", "https://")) and not download_missing_images:
            return None

        if existing.startswith(("http://", "https://")) and not refresh_images:
            downloaded = self._download_image(existing, product, "db_url")
            if downloaded:
                self.repo.update_product_image_path(product["product_id"], downloaded)
                return downloaded

        if not download_missing_images:
            return None

        for image_url in self._candidate_image_urls(product):
            downloaded = self._download_image(image_url, product, "web")
            if downloaded:
                self.repo.update_product_image_path(product["product_id"], downloaded)
                return downloaded
        return None

    def _local_existing_image(self, value: str) -> Optional[str]:
        if not value or value.startswith(("http://", "https://")):
            return None
        candidates = [Path(value), Path(os.getcwd()) / value]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return str(candidate)
        return None

    def _is_generated_placeholder(self, image_path: str) -> bool:
        return Path(image_path).name.startswith("placeholder_")

    def _candidate_image_urls(self, product: Dict) -> Iterable[str]:
        code = str(product.get("barcode") or product.get("product_code") or "").strip()
        name = str(product.get("product_name") or "").strip()
        isbn_candidates = self._isbn_candidates(code)
        is_book = bool(isbn_candidates) or self._looks_like_book(name)

        for isbn in isbn_candidates:
            yield f"https://covers.openlibrary.org/b/isbn/{urllib.parse.quote(isbn)}-L.jpg?default=false"
            try:
                google_cover = self._find_google_books_cover(isbn)
                if google_cover:
                    yield google_cover
            except Exception:
                pass

        if is_book:
            try:
                google_cover = self._find_google_books_cover_by_query(name)
                if google_cover:
                    yield google_cover
            except Exception:
                pass
            openlibrary_cover = self._find_openlibrary_cover_by_query(name)
            if openlibrary_cover:
                yield openlibrary_cover
            verified = self._find_verified_web_image(name, "book cover", code)
            if verified:
                yield verified
            return

        for finder in (
            self._find_openfoodfacts_image,
            self._find_openproductsfacts_image,
        ):
            try:
                image_url = finder(code, name)
                if image_url:
                    yield image_url
            except Exception:
                continue

        verified = self._find_verified_web_image(name, "product photo", code)
        if verified:
            yield verified

    def _isbn_candidates(self, code: str) -> List[str]:
        digits = re.sub(r"\D+", "", code or "")
        candidates = []
        if len(digits) in (10, 13):
            candidates.append(digits)
        if len(digits) > 13:
            candidates.append(digits[-13:])
        if digits.startswith("978") and len(digits) >= 12:
            candidates.append(digits[:13])
        return list(dict.fromkeys(candidates))

    def _looks_like_book(self, name: str) -> bool:
        lowered = str(name or "").lower()
        markers = ("كتاب", "رواية", "قصة", "قصص", "مجلة", "book", "novel")
        return any(marker in lowered for marker in markers)

    def _has_barcode_shape(self, code: str) -> bool:
        digits = re.sub(r"\D+", "", code or "")
        return 8 <= len(digits) <= 14

    def _find_google_books_cover(self, isbn: str) -> Optional[str]:
        data = self._http_json(
            "https://www.googleapis.com/books/v1/volumes?q=isbn:"
            f"{urllib.parse.quote(isbn)}"
        )
        for item in data.get("items", []) if data else []:
            links = item.get("volumeInfo", {}).get("imageLinks", {})
            image_url = (
                links.get("extraLarge")
                or links.get("large")
                or links.get("medium")
                or links.get("thumbnail")
            )
            if image_url:
                return image_url.replace("http://", "https://")
        return None

    def _find_google_books_cover_by_query(self, name: str) -> Optional[str]:
        if not name:
            return None
        data = self._http_json(
            "https://www.googleapis.com/books/v1/volumes?q="
            f"{urllib.parse.quote(name)}&maxResults=3"
        )
        for item in data.get("items", []) if data else []:
            links = item.get("volumeInfo", {}).get("imageLinks", {})
            image_url = (
                links.get("extraLarge")
                or links.get("large")
                or links.get("medium")
                or links.get("thumbnail")
            )
            if image_url:
                return image_url.replace("http://", "https://")
        return None

    def _find_openlibrary_cover_by_query(self, name: str) -> Optional[str]:
        if not name:
            return None
        data = self._http_json(
            "https://openlibrary.org/search.json?"
            f"title={urllib.parse.quote(name)}&limit=5&fields=cover_i,isbn,title"
        )
        for doc in data.get("docs", []) if data else []:
            cover_id = doc.get("cover_i")
            if cover_id:
                return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
            for isbn in doc.get("isbn", [])[:3]:
                if isbn:
                    return f"https://covers.openlibrary.org/b/isbn/{urllib.parse.quote(isbn)}-L.jpg?default=false"
        return None

    def _find_openfoodfacts_image(self, code: str, name: str) -> Optional[str]:
        digits = re.sub(r"\D+", "", code or "")
        if not digits or len(digits) < 7:
            return None
        data = self._http_json(
            "https://world.openfoodfacts.org/api/v2/product/"
            f"{urllib.parse.quote(digits)}.json?fields=image_front_url,image_url"
        )
        product = data.get("product") if data else None
        if not product:
            return None
        return product.get("image_front_url") or product.get("image_url")

    def _find_openproductsfacts_image(self, code: str, name: str) -> Optional[str]:
        digits = re.sub(r"\D+", "", code or "")
        if not digits or len(digits) < 7:
            return None
        data = self._http_json(
            "https://world.openproductsfacts.org/api/v2/product/"
            f"{urllib.parse.quote(digits)}.json?fields=image_front_url,image_url"
        )
        product = data.get("product") if data else None
        if not product:
            return None
        return product.get("image_front_url") or product.get("image_url")

    def _find_bing_image(self, code: str, name: str) -> Optional[str]:
        query = " ".join(part for part in [code, name, "product photo"] if part).strip()
        if not query:
            return None
        page = self._http_text(
            "https://www.bing.com/images/search?q="
            f"{urllib.parse.quote(query)}&form=HDRSC2&first=1"
        )
        for pattern in (r'"murl"\s*:\s*"([^"]+)"', r"murl&quot;:&quot;([^&]+)&quot;"):
            for match in re.finditer(pattern, page or ""):
                image_url = match.group(1).replace("\\/", "/")
                image_url = image_url.replace("&amp;", "&")
                if image_url.startswith(("http://", "https://")):
                    return image_url
        return None

    def _find_duckduckgo_image(self, code: str, name: str) -> Optional[str]:
        query = " ".join(part for part in [code, name, "product"] if part).strip()
        if not query:
            return None
        encoded = urllib.parse.quote(query)
        page = self._http_text(
            f"https://duckduckgo.com/?q={encoded}&iax=images&ia=images"
        )
        match = re.search(r"vqd=['\"]?([^'\"&]+)", page or "")
        if not match:
            return None
        data = self._http_json(
            "https://duckduckgo.com/i.js?"
            f"l=us-en&o=json&q={encoded}&vqd={urllib.parse.quote(match.group(1))}&f=,,,&p=1"
        )
        for result in data.get("results", []) if data else []:
            image_url = result.get("image") or result.get("thumbnail")
            if image_url:
                return image_url
        return None

    def _find_verified_web_image(
        self, product_name: str, suffix: str, code: str = ""
    ) -> Optional[str]:
        tokens = self._meaningful_tokens(f"{code} {product_name}")
        if not tokens:
            return None
        query = f"{code} {product_name} {suffix}".strip()
        for finder in (
            self._bing_verified_candidates,
            self._duckduckgo_verified_candidates,
        ):
            for title, image_url in finder(query):
                if self._is_relevant_image_result(product_name, title, image_url, code):
                    return image_url
        return None

    def _bing_verified_candidates(self, query: str) -> Iterable[tuple[str, str]]:
        page = self._http_text(
            "https://www.bing.com/images/search?q="
            f"{urllib.parse.quote(query)}&form=HDRSC2&first=1"
        )
        if not page:
            return []
        candidates = []
        pattern = r'"t"\s*:\s*"([^"]+)".{0,800}?"murl"\s*:\s*"([^"]+)"'
        for match in re.finditer(pattern, page, re.DOTALL):
            title = self._clean_web_text(match.group(1))
            image_url = self._clean_web_text(match.group(2)).replace("\\/", "/")
            if image_url.startswith(("http://", "https://")):
                candidates.append((title, image_url))
        if candidates:
            return candidates[:8]
        for match in re.finditer(r'"murl"\s*:\s*"([^"]+)"', page):
            image_url = self._clean_web_text(match.group(1)).replace("\\/", "/")
            if image_url.startswith(("http://", "https://")):
                candidates.append((image_url, image_url))
        return candidates[:5]

    def _duckduckgo_verified_candidates(self, query: str) -> Iterable[tuple[str, str]]:
        encoded = urllib.parse.quote(query)
        page = self._http_text(
            f"https://duckduckgo.com/?q={encoded}&iax=images&ia=images"
        )
        match = re.search(r"vqd=['\"]?([^'\"&]+)", page or "")
        if not match:
            return []
        data = self._http_json(
            "https://duckduckgo.com/i.js?"
            f"l=us-en&o=json&q={encoded}&vqd={urllib.parse.quote(match.group(1))}&f=,,,&p=1"
        )
        candidates = []
        for result in data.get("results", []) if data else []:
            image_url = result.get("image") or result.get("thumbnail")
            title = result.get("title") or result.get("source") or ""
            if image_url:
                candidates.append((title, image_url))
        return candidates[:8]

    def _is_relevant_image_result(
        self, product_name: str, title: str, image_url: str, code: str = ""
    ) -> bool:
        tokens = self._meaningful_tokens(product_name)
        haystack = self._normalize_text(f"{title} {image_url}")
        digits = re.sub(r"\D+", "", code or "")
        if digits and digits in re.sub(r"\D+", "", haystack):
            return True
        if not tokens or not haystack:
            return False
        matched = sum(1 for token in tokens if token in haystack)
        if len(tokens) <= 2:
            return matched == len(tokens)
        return matched >= max(2, int(len(tokens) * 0.45))

    def _meaningful_tokens(self, text: str) -> List[str]:
        normalized = self._normalize_text(text)
        stop_words = {
            "كجم",
            "جم",
            "جرام",
            "قطعة",
            "كبسولة",
            "كبسولات",
            "عبوة",
            "the",
            "and",
            "for",
            "with",
            "product",
            "photo",
            "book",
            "cover",
        }
        tokens = []
        for token in normalized.split():
            if token in stop_words:
                continue
            if len(token) < 3 and not token.isdigit():
                continue
            tokens.append(token)
        return list(dict.fromkeys(tokens))[:8]

    def _normalize_text(self, text: str) -> str:
        text = self._clean_web_text(text).lower()
        replacements = {
            "أ": "ا",
            "إ": "ا",
            "آ": "ا",
            "ة": "ه",
            "ى": "ي",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"[^\w\u0600-\u06FF]+", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()

    def _clean_web_text(self, text: str) -> str:
        return (
            urllib.parse.unquote(str(text or ""))
            .replace("&quot;", '"')
            .replace("&amp;", "&")
        )

    def _html_text(self, text: str) -> str:
        escaped = (
            str(text or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return escaped.replace("\n", "<br>")

    def _download_image(
        self, image_url: str, product: Dict, source: str
    ) -> Optional[str]:
        try:
            request = urllib.request.Request(
                image_url, headers={"User-Agent": self.USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=14) as response:
                data = response.read(5 * 1024 * 1024)
            if len(data) < 500:
                return None

            temp_path = self.image_dir / self._safe_filename(
                f"{product.get('product_code') or product.get('product_id')}_{source}.tmp"
            )
            temp_path.write_bytes(data)
            final_path = self.image_dir / self._safe_filename(
                f"{product.get('product_code') or product.get('product_id')}.jpg"
            )
            try:
                with Image.open(temp_path) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    if image.width < 80 or image.height < 80:
                        return None
                    image.thumbnail((900, 650), Image.Resampling.LANCZOS)
                    canvas = Image.new("RGB", (900, 650), "white")
                    x = (900 - image.width) // 2
                    y = (650 - image.height) // 2
                    canvas.paste(image, (x, y))
                    canvas.save(final_path, "JPEG", quality=92)
            finally:
                if temp_path.exists():
                    temp_path.unlink()
            return str(final_path)
        except Exception:
            return None

    def _save_catalog_pdf(
        self, products: List[Dict], filename_prefix: str
    ) -> Optional[str]:
        output_dir = self._catalog_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / f"{filename_prefix}.pdf"

        writer = QPdfWriter(str(pdf_path))
        writer.setResolution(72)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setPageLayout(
            QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(0, 0, 0, 0),
                QPageLayout.Unit.Point,
            )
        )

        painter = QPainter(writer)
        if not painter.isActive():
            return None
        try:
            self._draw_cover(painter, products)
            writer.newPage()
            for page_index, chunk in enumerate(self._chunks(products, 4), 1):
                self._draw_products_page(painter, chunk, page_index)
                if page_index * 4 < len(products):
                    writer.newPage()
        finally:
            painter.end()

        if pdf_path.exists():
            self._open_file(pdf_path)
            return str(pdf_path)
        return None

    def _draw_cover(self, painter: QPainter, products: List[Dict]):
        self._fill_page(painter, QColor("#0f3d24"))
        self._draw_text(
            painter,
            QRectF(40, 70, 515, 34),
            "POS V2 OFFERS CATALOG",
            15,
            "#bbf7d0",
            bold=True,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        self._draw_text(
            painter,
            QRectF(45, 160, 505, 95),
            "مجلة العروض",
            48,
            COLORS["text_on_brand"],
            bold=True,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        self._draw_text(
            painter,
            QRectF(45, 258, 505, 42),
            "أفضل العروض المتاحة الآن",
            20,
            "#dcfce7",
            align=Qt.AlignmentFlag.AlignCenter,
        )

        painter.setPen(QPen(QColor("#86efac"), 2))
        painter.setBrush(QColor("#14532d"))
        painter.drawRoundedRect(QRectF(72, 350, 452, 160), 24, 24)

        promo_names = sorted(
            {str(product.get("promotion_name") or "عرض خاص") for product in products}
        )
        info = f"عدد الأصناف: {len(products)}\nعدد العروض: {len(promo_names)}\n{self._short_join(promo_names)}"
        self._draw_text(
            painter,
            QRectF(92, 376, 412, 116),
            info,
            15,
            COLORS["text_on_brand"],
            bold=True,
            align=Qt.AlignmentFlag.AlignCenter,
        )

        footer = f"تم الإنشاء في {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self._draw_text(
            painter,
            QRectF(45, 760, 505, 30),
            footer,
            12,
            "#bbf7d0",
            align=Qt.AlignmentFlag.AlignCenter,
        )

    def _draw_products_page(
        self, painter: QPainter, products: List[Dict], page_index: int
    ):
        self._fill_page(painter, QColor("#f8fafc"))
        self._draw_text(
            painter,
            QRectF(28, 22, 539, 38),
            "منتجات العروض",
            24,
            "#14532d",
            bold=True,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        self._draw_text(
            painter,
            QRectF(28, 58, 539, 22),
            f"صفحة {page_index}",
            10,
            "#64748b",
            align=Qt.AlignmentFlag.AlignCenter,
        )

        card_width = 258
        card_height = 345
        positions = [(35, 98), (302, 98), (35, 455), (302, 455)]
        for product, (x, y) in zip(products, positions):
            self._draw_product_card(
                painter, product, QRectF(x, y, card_width, card_height)
            )

    def _draw_product_card(self, painter: QPainter, product: Dict, rect: QRectF):
        painter.setPen(QPen(QColor("#dcfce7"), 1.5))
        painter.setBrush(QColor(COLORS["text_on_brand"]))
        painter.drawRoundedRect(rect, 18, 18)

        image_rect = QRectF(rect.x() + 16, rect.y() + 18, rect.width() - 32, 160)
        self._draw_product_image(
            painter, product.get("resolved_image_path"), image_rect
        )

        name_rect = QRectF(rect.x() + 14, rect.y() + 190, rect.width() - 28, 58)
        self._draw_text(
            painter,
            name_rect,
            str(product.get("product_name") or ""),
            14,
            "#0f172a",
            bold=True,
            align=Qt.AlignmentFlag.AlignCenter,
            wrap=True,
        )

        original_price = float(product.get("sell_price") or 0)
        offer_price = self._offer_price(product, original_price)
        price = offer_price if offer_price is not None else original_price
        self._draw_text(
            painter,
            QRectF(rect.x() + 20, rect.y() + 254, rect.width() - 40, 34),
            self._price_text(product, price),
            22,
            "#16a34a",
            bold=True,
            align=Qt.AlignmentFlag.AlignCenter,
        )
        if (
            product.get("promo_type") != "bundle_price"
            and offer_price is not None
            and offer_price < original_price
        ):
            self._draw_text(
                painter,
                QRectF(rect.x() + 20, rect.y() + 290, rect.width() - 40, 20),
                f"بدلاً من {original_price:,.2f} ج.م",
                10,
                "#94a3b8",
                align=Qt.AlignmentFlag.AlignCenter,
            )

        badge_rect = QRectF(rect.x() + 42, rect.y() + 315, rect.width() - 84, 24)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#dcfce7"))
        painter.drawRoundedRect(badge_rect, 12, 12)
        self._draw_text(
            painter,
            badge_rect,
            str(product.get("promotion_name") or "عرض خاص"),
            10,
            "#166534",
            bold=True,
            align=Qt.AlignmentFlag.AlignCenter,
        )

    def _price_text(self, product: Dict, price: float) -> str:
        if product.get("promo_type") == "bundle_price":
            companion = product.get("bundle_product_name") or "المنتج المرافق"
            return f"باقة مع {companion}: {price:,.2f} ج.م"
        return f"{price:,.2f} ج.م"

    def _deduplicate_products(self, products: List[Dict]) -> List[Dict]:
        selected = {}
        for product in products:
            product_id = product.get("product_id")
            if product_id is None:
                selected[id(product)] = product
                continue

            current = selected.get(product_id)
            if current is None:
                selected[product_id] = product
                continue

            original_price = float(product.get("sell_price") or 0)
            current_price = self._offer_price(current, original_price)
            candidate_price = self._offer_price(product, original_price)
            current_discount = original_price - (
                current_price if current_price is not None else original_price
            )
            candidate_discount = original_price - (
                candidate_price if candidate_price is not None else original_price
            )
            if candidate_discount > current_discount:
                selected[product_id] = product
        return list(selected.values())

    def _draw_product_image(
        self, painter: QPainter, image_path: Optional[str], rect: QRectF
    ):
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        painter.setBrush(QColor("#f8fafc"))
        painter.drawRoundedRect(rect, 14, 14)
        if not image_path or not os.path.exists(image_path):
            self._draw_text(
                painter,
                QRectF(rect.x() + 12, rect.y() + 48, rect.width() - 24, 34),
                "الصورة غير متوفرة",
                13,
                "#64748b",
                bold=True,
                align=Qt.AlignmentFlag.AlignCenter,
            )
            self._draw_text(
                painter,
                QRectF(rect.x() + 12, rect.y() + 84, rect.width() - 24, 42),
                "لم يتم العثور على صورة موثوقة لهذا الصنف",
                9,
                "#94a3b8",
                align=Qt.AlignmentFlag.AlignCenter,
                wrap=True,
            )
            return
        image = QImage(str(image_path))
        if image.isNull():
            self._draw_text(
                painter,
                rect,
                "الصورة غير متوفرة",
                13,
                "#94a3b8",
                bold=True,
                align=Qt.AlignmentFlag.AlignCenter,
            )
            return
        scaled = image.scaled(
            int(rect.width() - 14),
            int(rect.height() - 14),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = rect.x() + (rect.width() - scaled.width()) / 2
        y = rect.y() + (rect.height() - scaled.height()) / 2
        painter.drawImage(QRectF(x, y, scaled.width(), scaled.height()), scaled)

    def _fill_page(self, painter: QPainter, color: QColor):
        painter.fillRect(QRectF(0, 0, self.PAGE_WIDTH, self.PAGE_HEIGHT), color)

    def _draw_text(
        self,
        painter: QPainter,
        rect: QRectF,
        text: str,
        size: int,
        color: str,
        bold: bool = False,
        align=Qt.AlignmentFlag.AlignRight,
        wrap: bool = False,
    ):
        font = QFont("Segoe UI", size)
        font.setBold(bold)
        document = QTextDocument()
        document.setDefaultFont(font)
        document.setDocumentMargin(0)
        document.setTextWidth(rect.width())

        align_css = "center"
        if align == Qt.AlignmentFlag.AlignRight:
            align_css = "right"
        elif align == Qt.AlignmentFlag.AlignLeft:
            align_css = "left"

        white_space = "normal" if wrap else "nowrap"
        safe_text = self._html_text(text)
        document.setHtml(f"""
            <div dir="rtl" style="
                color:{color};
                text-align:{align_css};
                font-size:{size}pt;
                font-weight:{'800' if bold else '400'};
                white-space:{white_space};
                line-height:1.25;
            ">{safe_text}</div>
            """)
        painter.save()
        painter.translate(rect.topLeft())
        document.drawContents(painter, QRectF(0, 0, rect.width(), rect.height()))
        painter.restore()

    def _offer_price(self, product: Dict, original_price: float) -> Optional[float]:
        promo_type = product.get("promo_type")
        value = float(product.get("value") or 0)
        if promo_type == "percentage":
            return max(round(original_price * (1 - value / 100), 2), 0)
        if promo_type == "fixed":
            return max(round(original_price - value, 2), 0)
        if promo_type == "fixed_per_unit":
            return max(round(original_price - value, 2), 0)
        if promo_type == "min_qty_discount":
            return max(round(original_price * (1 - value / 100), 2), 0)
        if promo_type == "second_item_percentage":
            discount = original_price * (value / 100) / 2
            return max(round(original_price - discount, 2), 0)
        if promo_type == "second_item_fixed":
            return max(round(original_price - min(value, original_price) / 2, 2), 0)
        if promo_type == "buy_x_get_y":
            buy_quantity = max(int(product.get("buy_quantity") or 0), 0)
            free_quantity = max(int(value), 0)
            group_size = buy_quantity + free_quantity
            if buy_quantity and free_quantity and group_size:
                return round(original_price * buy_quantity / group_size, 2)
        if promo_type == "bundle_price":
            bundle_price = float(product.get("bundle_price") or value or 0)
            return max(round(bundle_price, 2), 0) if bundle_price > 0 else None
        return None

    def _catalog_output_dir(self) -> Path:
        arabic_months = {
            1: "يناير",
            2: "فبراير",
            3: "مارس",
            4: "أبريل",
            5: "مايو",
            6: "يونيو",
            7: "يوليو",
            8: "أغسطس",
            9: "سبتمبر",
            10: "أكتوبر",
            11: "نوفمبر",
            12: "ديسمبر",
        }
        now = datetime.now()
        return (
            Path(os.getcwd())
            / "الفواتير"
            / "العروض"
            / "مجلة العروض"
            / str(now.year)
            / arabic_months[now.month]
        )

    def _open_file(self, path: Path):
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception:
            pass

    def _chunks(self, items: List[Dict], size: int) -> Iterable[List[Dict]]:
        for index in range(0, len(items), size):
            yield items[index : index + size]

    def _http_text(self, url: str) -> str:
        if url in self._http_cache:
            return self._http_cache[url]
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": self.USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                text = response.read(2 * 1024 * 1024).decode("utf-8", errors="ignore")
                self._http_cache[url] = text
                return text
        except Exception:
            self._http_cache[url] = ""
            return ""

    def _http_json(self, url: str) -> Dict:
        text = self._http_text(url)
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    def _safe_filename(self, value: str) -> str:
        clean = re.sub(r"[^\w\-.]+", "_", value, flags=re.UNICODE).strip("_")
        return clean or "product_image.jpg"

    def _wrap_text(self, text: str, width: int) -> str:
        words = str(text or "").split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > width and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return "\n".join(lines[:4])

    def _short_join(self, values: List[str]) -> str:
        text = " - ".join(values[:4])
        if len(values) > 4:
            text += f" + {len(values) - 4} عروض أخرى"
        return text
