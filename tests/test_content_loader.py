"""Regression tests for content-pack loading and fallback behavior."""

from src import content_loader


def test_get_pack_data_reads_active_pack_resource():
    content_loader.clear_content_cache()

    data = content_loader.get_pack_data("fantasy_core", "classes.json")

    assert "classes" in data
    assert "warrior" in data["classes"]


def test_get_pack_data_falls_back_to_legacy_flat_file():
    content_loader.clear_content_cache()

    data = content_loader.get_pack_data("fantasy_core", "starter_kits.json")

    assert isinstance(data, dict)
    assert data


def test_get_session_pack_data_defaults_to_default_pack():
    content_loader.clear_content_cache()

    data = content_loader.get_session_pack_data({}, "races.json")

    assert "races" in data
    assert "human" in data["races"]
