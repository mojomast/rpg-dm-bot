"""Content-pack loading helpers for theme-scoped static game data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONTENT_PACK_ID = "fantasy_core"
REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_DATA_ROOT = REPO_ROOT / "data" / "game_data"
MANIFEST_PATH = GAME_DATA_ROOT / "manifests" / "content_packs.json"


def _load_manifest() -> Dict[str, Any]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_content_pack_manifest(content_pack_id: str = DEFAULT_CONTENT_PACK_ID) -> Dict[str, Any]:
    manifest = _load_manifest()
    pack = manifest.get("packs", {}).get(content_pack_id)
    if not pack:
        raise FileNotFoundError(f"Unknown content pack: {content_pack_id}")
    return pack


def load_content_file(filename: str, content_pack_id: str = DEFAULT_CONTENT_PACK_ID) -> Dict[str, Any]:
    pack = get_content_pack_manifest(content_pack_id)
    pack_path = GAME_DATA_ROOT / pack["path"] / filename
    if not pack_path.exists():
        raise FileNotFoundError(f"Missing content file '{filename}' for pack '{content_pack_id}'")
    with pack_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_session_content_file(session: Dict[str, Any] | None, filename: str) -> Dict[str, Any]:
    content_pack_id = (session or {}).get("content_pack_id") or DEFAULT_CONTENT_PACK_ID
    return load_content_file(filename, content_pack_id=content_pack_id)
