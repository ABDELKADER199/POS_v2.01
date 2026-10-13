"""
Tests for builder.config – validation rules and data integrity.

These tests run **without Qt** and verify:
    1. All edition presets have valid structure
    2. No duplicate feature keys in presets
    3. Client/app name validation
    4. Feature / role count validation
    5. All preset feature keys exist in FEATURE_CATALOG
    6. All preset roles exist in ROLE_LABELS
    7. All permission labels cover every permission in FEATURE_CATALOG
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from builder.config import (
    EDITION_PRESETS,
    FEATURE_GROUP_LABELS,
    PERMISSION_LABELS,
    ROLE_LABELS,
    validate_all,
    validate_app_name,
    validate_client_name,
    validate_features,
    validate_roles,
    MAX_CLIENT_NAME_LENGTH,
)
from utils.feature_flags import ALL_FEATURE_KEYS, FEATURE_CATALOG
from utils.permissions import ROLE_PERMISSIONS


# ── Validation Tests ────────────────────────────────────────────────────


class TestValidateClientName:
    def test_empty_name_fails(self):
        ok, msg = validate_client_name("")
        assert not ok
        assert "اسم العميل" in msg

    def test_whitespace_only_fails(self):
        ok, msg = validate_client_name("   ")
        assert not ok

    def test_valid_name_passes(self):
        ok, msg = validate_client_name("سوبرماركت الأمل")
        assert ok
        assert msg == ""

    def test_too_long_name_fails(self):
        ok, msg = validate_client_name("x" * (MAX_CLIENT_NAME_LENGTH + 1))
        assert not ok
        assert "طويل" in msg

    def test_max_length_name_passes(self):
        ok, msg = validate_client_name("x" * MAX_CLIENT_NAME_LENGTH)
        assert ok


class TestValidateAppName:
    def test_empty_fails(self):
        ok, msg = validate_app_name("")
        assert not ok

    def test_valid_passes(self):
        ok, msg = validate_app_name("HyperPOS")
        assert ok


class TestValidateFeatures:
    def test_empty_list_fails(self):
        ok, msg = validate_features([])
        assert not ok
        assert "ميزة" in msg

    def test_one_feature_passes(self):
        ok, msg = validate_features(["cashier"])
        assert ok

    def test_many_features_passes(self):
        ok, msg = validate_features(list(ALL_FEATURE_KEYS))
        assert ok


class TestValidateRoles:
    def test_empty_fails(self):
        ok, msg = validate_roles([])
        assert not ok
        assert "دور" in msg

    def test_one_role_passes(self):
        ok, msg = validate_roles([99])
        assert ok


class TestValidateAll:
    def test_all_valid(self):
        ok, errors = validate_all("Client", "App", ["cashier"], [99])
        assert ok
        assert errors == []

    def test_collects_all_errors(self):
        ok, errors = validate_all("", "", [], [])
        assert not ok
        assert len(errors) == 4  # client, app, features, roles

    def test_partial_errors(self):
        ok, errors = validate_all("Client", "", ["cashier"], [99])
        assert not ok
        assert len(errors) == 1  # only app name


# ── Data Integrity Tests ───────────────────────────────────────────────


class TestEditionPresets:
    """Ensure all presets are well-formed and reference valid data."""

    @pytest.mark.parametrize("preset_key", list(EDITION_PRESETS.keys()))
    def test_preset_has_required_keys(self, preset_key: str):
        preset = EDITION_PRESETS[preset_key]
        assert "label" in preset, f"Preset '{preset_key}' missing 'label'"
        assert "features" in preset, f"Preset '{preset_key}' missing 'features'"
        assert "roles" in preset, f"Preset '{preset_key}' missing 'roles'"

    @pytest.mark.parametrize("preset_key", list(EDITION_PRESETS.keys()))
    def test_preset_features_exist_in_catalog(self, preset_key: str):
        """Every feature key referenced in a preset must exist in FEATURE_CATALOG."""
        preset = EDITION_PRESETS[preset_key]
        features = preset.get("features")
        if features is None:
            return  # "full" preset enables everything
        catalog_keys = set(ALL_FEATURE_KEYS)
        for fk in features:
            assert fk in catalog_keys, (
                f"Preset '{preset_key}' references unknown feature '{fk}'"
            )

    @pytest.mark.parametrize("preset_key", list(EDITION_PRESETS.keys()))
    def test_preset_roles_exist_in_labels(self, preset_key: str):
        """Every role ID in a preset must have a label."""
        preset = EDITION_PRESETS[preset_key]
        roles = preset.get("roles")
        if roles is None:
            return
        for role_id in roles:
            assert role_id in ROLE_LABELS, (
                f"Preset '{preset_key}' references unknown role ID {role_id}"
            )

    @pytest.mark.parametrize("preset_key", list(EDITION_PRESETS.keys()))
    def test_no_duplicate_features_in_preset(self, preset_key: str):
        """
        Feature sets are Python sets so duplicates are impossible at runtime,
        but this test documents the expectation and would catch list-based presets.
        """
        preset = EDITION_PRESETS[preset_key]
        features = preset.get("features")
        if features is None:
            return
        assert isinstance(features, set), (
            f"Preset '{preset_key}' features should be a set, got {type(features).__name__}"
        )

    def test_full_preset_enables_all(self):
        full = EDITION_PRESETS["full"]
        assert full["features"] is None
        assert full["roles"] is None


class TestRoleLabels:
    def test_all_roles_have_labels(self):
        for role_id in ROLE_PERMISSIONS:
            assert role_id in ROLE_LABELS, f"Role {role_id} missing label"

    def test_all_labels_are_nonempty(self):
        for role_id, label in ROLE_LABELS.items():
            assert label.strip(), f"Role {role_id} has empty label"


class TestPermissionLabels:
    def test_all_feature_permissions_have_labels(self):
        """Every permission referenced by FEATURE_CATALOG must have a label."""
        for feature in FEATURE_CATALOG:
            for perm in feature.permissions:
                assert perm in PERMISSION_LABELS, (
                    f"Permission '{perm}' (from feature '{feature.key}') has no label"
                )

    def test_all_labels_are_nonempty(self):
        for perm, label in PERMISSION_LABELS.items():
            assert label.strip(), f"Permission '{perm}' has empty label"


class TestFeatureGroupLabels:
    def test_all_top_level_features_have_group_labels(self):
        """Each top-level feature group (before the dot) must have a label."""
        top_groups = {f.key.split(".", 1)[0] for f in FEATURE_CATALOG}
        for group in top_groups:
            assert group in FEATURE_GROUP_LABELS, (
                f"Feature group '{group}' has no label in FEATURE_GROUP_LABELS"
            )


class TestFeatureCatalog:
    def test_no_duplicate_keys(self):
        keys = [f.key for f in FEATURE_CATALOG]
        assert len(keys) == len(set(keys)), "Duplicate keys in FEATURE_CATALOG"

    def test_every_feature_has_label(self):
        for f in FEATURE_CATALOG:
            assert f.label.strip(), f"Feature '{f.key}' has empty label"

    def test_every_feature_has_description(self):
        for f in FEATURE_CATALOG:
            assert f.description.strip(), f"Feature '{f.key}' has empty description"
