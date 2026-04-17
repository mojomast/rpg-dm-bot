"""Helpers for browser chat identity mapping."""

from __future__ import annotations

import hashlib
import uuid


def generate_web_identity_uuid() -> str:
    """Generate a server-issued UUID for web chat identity."""
    return str(uuid.uuid4())


def hash_ip_address(ip_address: str | None) -> str | None:
    """Hash a client IP before storing it."""
    if not ip_address:
        return None
    return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()


def web_user_id_from_uuid(uuid_value: str) -> int:
    """Map a stable browser UUID to a positive 63-bit integer user id."""
    digest = hashlib.sha256(uuid_value.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF
    return value or 1
