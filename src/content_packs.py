"""Compatibility wrappers for content-pack loading helpers."""

from typing import Any, Dict

from src.content_loader import (
    DEFAULT_CONTENT_PACK_ID,
    get_content_pack_manifest,
    get_pack_data,
    get_session_pack_data,
)


def load_content_file(filename: str, content_pack_id: str = DEFAULT_CONTENT_PACK_ID) -> Dict[str, Any]:
    return get_pack_data(content_pack_id, filename)


def load_session_content_file(session: Dict[str, Any] | None, filename: str) -> Dict[str, Any]:
    return get_session_pack_data(session, filename)
