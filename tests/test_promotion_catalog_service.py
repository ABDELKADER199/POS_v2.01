from services.promotion_catalog_service import PromotionCatalogService


def catalog_service():
    return PromotionCatalogService.__new__(PromotionCatalogService)


def test_offer_price_supports_catalog_discount_types():
    service = catalog_service()

    assert service._offer_price({"promo_type": "fixed_per_unit", "value": 3}, 10) == 7
    assert (
        service._offer_price({"promo_type": "min_qty_discount", "value": 25}, 20) == 15
    )
    assert (
        service._offer_price({"promo_type": "second_item_percentage", "value": 20}, 100)
        == 90
    )
    assert (
        service._offer_price({"promo_type": "second_item_fixed", "value": 10}, 100)
        == 95
    )
    assert (
        service._offer_price(
            {"promo_type": "buy_x_get_y", "buy_quantity": 2, "value": 1}, 10
        )
        == 6.67
    )
    assert (
        service._offer_price({"promo_type": "bundle_price", "bundle_price": 25}, 20)
        == 25
    )
    assert (
        service._price_text(
            {"promo_type": "bundle_price", "bundle_product_name": "منتج مرافق"}, 25
        )
        == "باقة مع منتج مرافق: 25.00 ج.م"
    )


def test_deduplicate_products_keeps_the_best_discount():
    service = catalog_service()
    products = [
        {"product_id": 1, "sell_price": 100, "promo_type": "percentage", "value": 10},
        {"product_id": 1, "sell_price": 100, "promo_type": "fixed", "value": 100},
        {"product_id": 2, "sell_price": 50, "promo_type": "fixed", "value": 5},
    ]

    result = service._deduplicate_products(products)

    assert len(result) == 2
    assert (
        next(product for product in result if product["product_id"] == 1)["value"]
        == 100
    )


def test_local_only_catalog_does_not_download_remote_image(monkeypatch):
    service = catalog_service()
    service.repo = object()

    def fail_download(*args, **kwargs):
        raise AssertionError("remote image download should not be attempted")

    monkeypatch.setattr(service, "_download_image", fail_download)

    result = service._resolve_product_image(
        {"image_path": "https://example.com/product.jpg", "product_id": 1},
        download_missing_images=False,
        refresh_images=False,
    )

    assert result is None
