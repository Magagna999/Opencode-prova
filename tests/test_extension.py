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
POPUP_JS_PATH = EXTENSION_DIR / "popup.js"

#: Manifest keys that describe permissions: they must be absent or empty.
PERMISSION_KEYS = (
    "permissions",
    "host_permissions",
    "optional_permissions",
    "optional_host_permissions",
)

#: Keys that only exist in Manifest V2 and must not appear in a MV3 manifest.
MV2_ONLY_KEYS = (
    "browser_action",
    "page_action",
    "background",
    "content_security_policy",
)

#: Chrome accepts one to four dot separated integers, without leading zeros.
VERSION_REGEX = r"(0|[1-9]\d*)(\.(0|[1-9]\d*)){0,3}"


def _read_text(path):
    """Return the UTF-8 text content of ``path``."""
    return path.read_text(encoding="utf-8")


def _has_element_with_attribute(html, attribute, value, tag_name=None):
    """Return ``True`` when an element of ``html`` declares ``attribute="value"``.

    ``tag_name`` optionally restricts the match to a single tag name.

    The attribute name must be preceded by whitespace (``\\s``), therefore
    look-alike attributes such as ``data-id`` are never mistaken for ``id``.
    The attribute must belong to the same tag, because the gap between the tag
    name and the attribute cannot contain the ``>`` closing character.
    """
    tag = r"[a-zA-Z][a-zA-Z0-9-]*" if tag_name is None else re.escape(tag_name)
    pattern = rf"""<{tag}\b[^>]*?\s{re.escape(attribute)}\s*=\s*(["']){re.escape(value)}\1"""
    return re.search(pattern, html, flags=re.IGNORECASE) is not None


def _script_elements(html):
    """Return a list of ``(attributes, body)`` pairs for every script element."""
    elements = []
    pattern = r"<script\b([^>]*)>(.*?)(?:</script\s*>|$)"
    for match in re.finditer(pattern, html, flags=re.IGNORECASE | re.DOTALL):
        elements.append((match.group(1), match.group(2)))
    return elements


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


@pytest.fixture(scope="module")
def popup_js():
    """Raw popup JavaScript, failing clearly if the file is missing."""
    assert POPUP_JS_PATH.is_file(), f"Missing popup script: {POPUP_JS_PATH}"
    return _read_text(POPUP_JS_PATH)


def test_manifest_is_valid_json_with_version_3(manifest):
    # json.loads already proves the file is valid JSON.
    assert manifest["manifest_version"] == 3


@pytest.mark.parametrize("field", ["name", "version", "description"])
def test_manifest_required_fields_are_non_empty(manifest, field):
    assert field in manifest, f"Missing manifest field: {field}"
    value = manifest[field]
    assert isinstance(value, str), f"Manifest field '{field}' must be a string"
    assert value.strip(), f"Manifest field '{field}' must not be empty"


def test_manifest_version_uses_the_chrome_version_format(manifest):
    # M4: one to four dot separated integers, no leading zeros.
    version = manifest["version"]
    assert re.fullmatch(VERSION_REGEX, version), (
        f"Manifest version {version!r} does not match {VERSION_REGEX!r}"
    )


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


@pytest.mark.parametrize(
    ("tag_name", "attribute", "filename"),
    [
        ("link", "href", "popup.css"),
        ("script", "src", "popup.js"),
    ],
)
def test_popup_links_assets_with_the_expected_tags(popup_html, tag_name, attribute, filename):
    # M6: the asset must be referenced by the proper tag, and the attribute
    # must be preceded by whitespace so that 'data-href' is not a match.
    assert _has_element_with_attribute(
        popup_html, attribute, filename, tag_name=tag_name
    ), f"popup.html has no <{tag_name}> element with {attribute}=\"{filename}\""
    assert (EXTENSION_DIR / filename).is_file(), f"Missing asset: {filename}"


@pytest.mark.parametrize("element_id", ["btn", "esito"])
def test_popup_contains_required_ids(popup_html, element_id):
    # M6: '\sid\s*=' must not match 'data-id="btn"'.
    assert _has_element_with_attribute(
        popup_html, "id", element_id
    ), f"popup.html has no element with id '{element_id}'"


def test_attribute_search_helper_ignores_lookalike_attributes():
    # M6: the fake markup uses 'data-id', which must not be read as 'id'.
    fake_html = '<div data-id="btn">'
    assert not _has_element_with_attribute(fake_html, "id", "btn")
    # Sanity check: the very same attribute on a real element is detected.
    assert _has_element_with_attribute('<div id="btn">', "id", "btn")


def test_popup_js_referenced_ids_exist_in_popup_html(popup_js, popup_html):
    # M5: every id used by popup.js must be present in popup.html.
    referenced_ids = set(
        re.findall(r"""getElementById\(\s*["']([^"']+)["']\s*\)""", popup_js)
    )
    assert referenced_ids, "popup.js does not reference any id via getElementById()"
    for element_id in sorted(referenced_ids):
        assert _has_element_with_attribute(
            popup_html, "id", element_id
        ), f"popup.html has no element with id '{element_id}' referenced by popup.js"


def test_popup_has_no_inline_script_blocks(popup_html):
    # M2: a <script> without a src attribute and with a body is inline code.
    scripts = _script_elements(popup_html)
    assert scripts, "popup.html does not load any script"
    for attributes, body in scripts:
        has_src = re.search(r"""\ssrc\s*=""", attributes, flags=re.IGNORECASE)
        assert has_src or not body.strip(), (
            "popup.html contains an inline <script> block without a src attribute"
        )
        assert not (has_src and body.strip()), (
            "popup.html contains a <script> element with both src and inline code"
        )


def test_popup_has_no_inline_event_handler_attributes(popup_html):
    # M2: 'onclick' and friends are inline code too.
    handlers = re.findall(r"""\s(on[a-zA-Z]+)\s*=""", popup_html, flags=re.IGNORECASE)
    assert not handlers, f"popup.html contains inline event handlers: {handlers}"


def test_popup_js_has_no_dynamic_code_evaluation(popup_js):
    # M2: 'eval(' and 'new Function(' are forbidden by the MV3 CSP.
    assert not re.search(r"\beval\s*\(", popup_js), "popup.js must not call eval()"
    assert not re.search(
        r"\bnew\s+Function\s*\(", popup_js
    ), "popup.js must not call new Function()"


@pytest.mark.parametrize("key", PERMISSION_KEYS)
def test_manifest_permission_keys_are_absent_or_empty(manifest, key):
    # M1: the key may be missing, but if present it must be an empty list.
    if key not in manifest:
        return
    value = manifest[key]
    assert isinstance(value, list), f"Manifest key '{key}' must be a list"
    assert value == [], f"Unexpected permissions requested in '{key}': {value}"


def test_manifest_has_no_content_scripts(manifest):
    # M1: the popup must not inject scripts into web pages.
    assert "content_scripts" not in manifest, (
        "Manifest must not declare 'content_scripts'"
    )


@pytest.mark.parametrize("key", MV2_ONLY_KEYS)
def test_manifest_has_no_mv2_only_keys(manifest, key):
    # M3: these keys belong to Manifest V2 only.
    assert key not in manifest, (
        f"Manifest V2 key '{key}' must not be present in a Manifest V3 manifest"
    )
