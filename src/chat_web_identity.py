"""Helpers for browser chat identity mapping."""

from __future__ import annotations

import hashlib


def web_user_id_from_uuid(uuid_value: str) -> int:
    """Map a stable browser UUID to a positive 63-bit integer user id."""
    digest = hashlib.sha256(uuid_value.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF
    return value or 1
