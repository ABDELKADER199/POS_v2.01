import json
from pathlib import Path
from uuid import uuid4

from utils.feature_flags import (
    clear_feature_config_cache,
    effective_role_permissions,
    filter_pages_for_enabled_features,
    get_feature_config_path,
    get_store_scope,
    is_role_allowed,
    effective_edition_role_id,
)
from utils.permissions import Permission, ROLE_ADMIN
from utils.permissions import PermissionPolicy, ROLE_DEVELOPER, ROLE_MANAGER


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test_tmp" / "feature_flags"


def _test_file(name: str) -> Path:
    root = TEST_TMP_ROOT / f"{name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root / "customer_features.json"


def test_feature_config_filters_pages_and_permissions(monkeypatch):
    config_path = _test_file("filters")
    config_path.write_text(
        json.dumps(
            {
                "enabled_features": ["cashier"],
                "enabled_permissions": [Permission.OPEN_DRAWER],
                "role_permissions": {str(ROLE_ADMIN): [Permission.OPEN_DRAWER, Permission.MANAGE_USERS]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(config_path))
    clear_feature_config_cache()

    try:
        assert filter_pages_for_enabled_features(["admin", "cashier", "products"]) == ["cashier"]
        assert effective_role_permissions(
            ROLE_ADMIN,
            {Permission.OPEN_DRAWER, Permission.MANAGE_USERS},
        ) == {Permission.OPEN_DRAWER}
    finally:
        clear_feature_config_cache()


def test_missing_feature_config_keeps_default_pages_and_permissions(monkeypatch):
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(_test_file("missing")))
    clear_feature_config_cache()

    try:
        assert filter_pages_for_enabled_features(["admin", "cashier"]) == ["admin", "cashier"]
        assert effective_role_permissions(ROLE_ADMIN, {Permission.OPEN_DRAWER}) == {Permission.OPEN_DRAWER}
    finally:
        clear_feature_config_cache()


def test_frozen_app_reads_feature_config_next_to_exe(monkeypatch):
    config_path = _test_file("frozen")
    config_path.write_text(
        json.dumps({"enabled_features": ["cashier"]}),
        encoding="utf-8",
    )
    monkeypatch.delenv("POS_FEATURES_CONFIG", raising=False)
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", str(config_path.parent / "HyperPOS_client.exe"))
    clear_feature_config_cache()

    try:
        assert get_feature_config_path() == config_path
        assert filter_pages_for_enabled_features(["admin", "cashier", "products"]) == ["cashier"]
    finally:
        clear_feature_config_cache()


def test_frozen_app_reads_feature_config_from_meipass(monkeypatch):
    config_path = _test_file("meipass")
    config_path.write_text(
        json.dumps({"enabled_features": ["cashier"]}),
        encoding="utf-8",
    )
    missing_exe_dir = config_path.parent / "exe"
    missing_exe_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("POS_FEATURES_CONFIG", raising=False)
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", str(missing_exe_dir / "HyperPOS_client.exe"))
    monkeypatch.setattr("sys._MEIPASS", str(config_path.parent), raising=False)
    clear_feature_config_cache()

    try:
        assert get_feature_config_path() == config_path
        assert filter_pages_for_enabled_features(["admin", "cashier", "products"]) == ["cashier"]
    finally:
        clear_feature_config_cache()


def test_developer_pages_are_limited_by_cashier_edition(monkeypatch):
    config_path = _test_file("developer_pages")
    config_path.write_text(
        json.dumps({"enabled_features": ["cashier", "drawer"]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(config_path))
    clear_feature_config_cache()

    try:
        policy = PermissionPolicy({"role_id": ROLE_DEVELOPER})
        assert policy.main_pages() == ["cashier", "drawer"]
    finally:
        clear_feature_config_cache()


def test_allowed_roles_limit_login_roles(monkeypatch):
    config_path = _test_file("allowed_roles")
    config_path.write_text(
        json.dumps({"allowed_roles": [2, 3]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(config_path))
    clear_feature_config_cache()

    try:
        assert is_role_allowed(2) is True
        assert is_role_allowed(3) is True
        assert is_role_allowed(99) is False
    finally:
        clear_feature_config_cache()


def test_store_scope_is_loaded_from_feature_config(monkeypatch):
    config_path = _test_file("store_scope")
    config_path.write_text(
        json.dumps({"store_scope": {"id": 12, "name": "فرع 12"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(config_path))
    clear_feature_config_cache()

    try:
        assert get_store_scope() == {"id": 12, "name": "فرع 12"}
    finally:
        clear_feature_config_cache()


def test_cashier_edition_can_open_developer_and_admin_as_branch_manager(monkeypatch):
    config_path = _test_file("role_overrides")
    config_path.write_text(
        json.dumps(
            {
                "enabled_features": ["cashier", "drawer"],
                "role_overrides": {str(ROLE_DEVELOPER): ROLE_MANAGER, str(ROLE_ADMIN): ROLE_MANAGER},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("POS_FEATURES_CONFIG", str(config_path))
    clear_feature_config_cache()

    try:
        assert effective_edition_role_id(ROLE_DEVELOPER) == ROLE_MANAGER
        assert effective_edition_role_id(ROLE_ADMIN) == ROLE_MANAGER
        developer_policy = PermissionPolicy({"role_id": ROLE_DEVELOPER})
        admin_policy = PermissionPolicy({"role_id": ROLE_ADMIN})
        assert developer_policy.original_role_id == ROLE_DEVELOPER
        assert developer_policy.role_id == ROLE_MANAGER
        assert admin_policy.role_id == ROLE_MANAGER
        assert developer_policy.main_pages() == ["cashier", "drawer"]
        assert admin_policy.main_pages() == ["cashier", "drawer"]
    finally:
        clear_feature_config_cache()
