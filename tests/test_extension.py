"""Tests for the Chrome Manifest V3 extension in ``extension/``.

Only the Python standard library is used to inspect the extension files.
"""

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTENSION_DIR = PROJECT_ROOT / "extension"
MANIFEST_PATH = EXTENSION_DIR / "manifest.json"
POPUP_PATH = EXTENSION_DIR / "popup.html"


def _read_text(path):
    """Return the UTF-8 text content of ``path``."""
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest():
    """Parsed manifest content, failing clearly if the file is missing."""
    assert MANIFEST_PATH.is_file(), f"Missing manifest: {MANIFEST_PATH}"
    return json.loads(_read_text(MANIFEST_PATH))


@pytest.fixture(scope="module")
def popup_html():
    """Raw popup HTML, failing clearly if the file is missing."""
    assert POPUP_PATH.is_file(), f"Missing popup: {POPUP_PATH}"
    return _read_text(POPUP_PATH)


def test_manifest_is_valid_json_with_version_3(manifest):
    # json.loads already proves the file is valid JSON.
    assert manifest["manifest_version"] == 3


@pytest.mark.parametrize("field", ["name", "version", "description"])
def test_manifest_required_fields_are_non_empty(manifest, field):
    assert field in manifest, f"Missing manifest field: {field}"
    value = manifest[field]
    assert isinstance(value, str), f"Manifest field '{field}' must be a string"
    assert value.strip(), f"Manifest field '{field}' must not be empty"


def test_action_default_popup_points_to_existing_file(manifest):
    assert "action" in manifest, "Missing 'action' key in manifest"
    assert "default_popup" in manifest["action"], "Missing 'action.default_popup'"
    assert manifest["action"]["default_popup"] == "popup.html"

    popup_file = EXTENSION_DIR / manifest["action"]["default_popup"]
    assert popup_file.is_file(), f"Popup file does not exist: {popup_file}"


@pytest.mark.parametrize(
    ("reference", "filename"),
    [
        (r"""href\s*=\s*["']popup\.css["']""", "popup.css"),
        (r"""src\s*=\s*["']popup\.js["']""", "popup.js"),
    ],
)
def test_popup_references_existing_assets(popup_html, reference, filename):
    assert re.search(reference, popup_html), f"popup.html does not reference {filename}"
    assert (EXTENSION_DIR / filename).is_file(), f"Missing asset: {filename}"


@pytest.mark.parametrize("element_id", ["btn", "esito"])
def test_popup_contains_required_ids(popup_html, element_id):
    pattern = rf"""id\s*=\s*["']{element_id}["']"""
    assert re.search(pattern, popup_html), f"popup.html has no element with id '{element_id}'"


def test_manifest_has_no_unnecessary_permissions(manifest):
    # The key may be absent, but if present it must be an empty list.
    permissions = manifest.get("permissions", [])
    assert isinstance(permissions, list), "'permissions' must be a list"
    assert permissions == [], f"Unexpected permissions requested: {permissions}"
