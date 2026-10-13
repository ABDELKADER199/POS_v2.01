from builder.config import EDITION_PRESETS
from utils.permissions import (
    ROLE_ACCOUNTANT,
    ROLE_ADMIN,
    ROLE_DEVELOPER,
    ROLE_MANAGER,
    ROLE_OWNER,
)


def test_branch_manager_preset_configuration():
    preset = EDITION_PRESETS["branch_manager"]

    assert preset["role_overrides"] == {
        ROLE_DEVELOPER: ROLE_MANAGER,
        ROLE_ADMIN: ROLE_MANAGER,
    }
    assert preset["roles"] == {
        ROLE_DEVELOPER,
        ROLE_OWNER,
        ROLE_ADMIN,
        ROLE_MANAGER,
    }

    enabled_features = preset["features"]
    assert "stats" in enabled_features
    assert "products" in enabled_features
    assert "inventory_count" in enabled_features
    assert "accounts.expenses" in enabled_features
    assert "cashier" in enabled_features
    assert "drawer" in enabled_features

    assert "admin" not in enabled_features
    assert "purchases" not in enabled_features
    assert "promotions" not in enabled_features
    assert "settings" not in enabled_features
    assert ROLE_ACCOUNTANT not in preset["roles"]
