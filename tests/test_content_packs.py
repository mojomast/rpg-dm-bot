import pytest

from src.content_packs import DEFAULT_CONTENT_PACK_ID, get_content_pack_manifest, load_content_file


def test_default_content_pack_manifest_resolves():
    manifest = get_content_pack_manifest()
    assert manifest["id"] == DEFAULT_CONTENT_PACK_ID
    assert manifest["theme"] == "fantasy"


def test_load_classes_from_default_pack():
    data = load_content_file("classes.json")
    assert "classes" in data
    assert "warrior" in data["classes"]


def test_load_spells_from_default_pack():
    data = load_content_file("spells.json")
    assert "spells" in data
    assert "fire_bolt" in data["spells"]


def test_unknown_content_pack_raises():
    with pytest.raises(FileNotFoundError):
        get_content_pack_manifest("missing_pack")


def test_missing_file_in_valid_pack_raises():
    with pytest.raises(FileNotFoundError):
        load_content_file("missing.json")
