import pytest

from src.content_loader import DEFAULT_CONTENT_PACK_ID, clear_content_cache, get_pack_data


def test_get_pack_data_returns_default_pack_content():
    clear_content_cache()

    data = get_pack_data(DEFAULT_CONTENT_PACK_ID, "classes.json")

    assert "classes" in data
    assert "warrior" in data["classes"]


def test_get_pack_data_raises_for_missing_resource():
    clear_content_cache()

    with pytest.raises(FileNotFoundError):
        get_pack_data(DEFAULT_CONTENT_PACK_ID, "does_not_exist.json")
