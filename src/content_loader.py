"""Content-pack loader with manifest caching and legacy fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONTENT_PACK_ID = "fantasy_core"
REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_DATA_ROOT = REPO_ROOT / "data" / "game_data"
CONTENT_PACKS_MANIFEST_PATH = GAME_DATA_ROOT / "manifests" / "content_packs.json"
THEMES_MANIFEST_PATH = GAME_DATA_ROOT / "manifests" / "themes.json"

_MANIFEST_CACHE: Dict[str, Any] | None = None
_PACK_DATA_CACHE: dict[tuple[str, str], Dict[str, Any]] = {}


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def clear_content_cache() -> None:
    """Clear manifest and data caches for tests or reloads."""
    global _MANIFEST_CACHE
    _MANIFEST_CACHE = None
    _PACK_DATA_CACHE.clear()


def get_content_packs_manifest() -> Dict[str, Any]:
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        _MANIFEST_CACHE = _read_json(CONTENT_PACKS_MANIFEST_PATH)
    return _MANIFEST_CACHE


def get_themes_manifest() -> Dict[str, Any]:
    return _read_json(THEMES_MANIFEST_PATH)


def get_content_pack_manifest(content_pack_id: str = DEFAULT_CONTENT_PACK_ID) -> Dict[str, Any]:
    manifest = get_content_packs_manifest()
    pack = manifest.get("packs", {}).get(content_pack_id)
    if not pack:
        raise FileNotFoundError(f"Unknown content pack: {content_pack_id}")
    return pack


def _get_pack_data_root(pack: Dict[str, Any]) -> Path:
    relative_path = pack.get("data_path") or pack.get("path")
    if not relative_path:
        raise FileNotFoundError(f"Content pack '{pack.get('id', 'unknown')}' has no data path")
    return GAME_DATA_ROOT / relative_path


def get_pack_data(content_pack_id: str = DEFAULT_CONTENT_PACK_ID, resource: str = "") -> Dict[str, Any]:
    """Load a content-pack resource, falling back to the legacy flat file."""
    cache_key = (content_pack_id or DEFAULT_CONTENT_PACK_ID, resource)
    if cache_key in _PACK_DATA_CACHE:
        return _PACK_DATA_CACHE[cache_key]

    pack = get_content_pack_manifest(cache_key[0])
    pack_path = _get_pack_data_root(pack) / resource
    legacy_path = GAME_DATA_ROOT / resource

    if pack_path.exists():
        data = _read_json(pack_path)
    elif legacy_path.exists():
        data = _read_json(legacy_path)
    else:
        raise FileNotFoundError(
            f"Missing content file '{resource}' for pack '{cache_key[0]}' and legacy fallback"
        )

    _PACK_DATA_CACHE[cache_key] = data
    return data


def get_session_pack_data(session: Dict[str, Any] | None, resource: str) -> Dict[str, Any]:
    content_pack_id = (session or {}).get("content_pack_id") or DEFAULT_CONTENT_PACK_ID
    return get_pack_data(content_pack_id, resource)
