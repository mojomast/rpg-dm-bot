"""Shared utility helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.content_packs import load_session_content_file

ALLOWED_BOT_CHANNEL_ID = 1494536176453816431


def get_character_class(character: dict, default: str = "Unknown") -> str:
    """Return the normalized character class field used across older/newer rows."""
    return character.get('char_class') or character.get('class') or default


def is_allowed_bot_channel(channel_id: Optional[int]) -> bool:
    """Return True only for the single approved Discord channel."""
    return channel_id == ALLOWED_BOT_CHANNEL_ID


async def ensure_interaction_owner(interaction, owner_user_id: int, resource: str = "this interface") -> bool:
    """Reject interactions from users other than the original owner."""
    if interaction.user.id == owner_user_id:
        return True

    message = f"❌ Only the original player can use {resource}."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
    return False


async def send_chunked(target, content: str, view=None, max_len: int = 2000):
    """Send long text content in Discord-sized chunks."""
    chunks = [content[i:i + max_len] for i in range(0, len(content), max_len)] or [""]
    for index, chunk in enumerate(chunks):
        kwargs = {'view': view} if view and index == len(chunks) - 1 else {}
        await target.send(chunk, **kwargs)


async def resolve_runtime_session(
    db,
    *,
    guild_id: Optional[int] = None,
    user_id: Optional[int] = None,
    channel_id: Optional[int] = None,
    session_id: Optional[int] = None,
    character: Optional[Dict[str, Any]] = None,
    statuses: Optional[list[str]] = None,
):
    """Resolve the best session for a live Discord/runtime lookup."""
    statuses = statuses or ['active', 'paused', 'inactive']

    if session_id:
        session = await db.get_session(session_id)
        if session:
            return session

    character_session_id = (character or {}).get('session_id')
    if character_session_id:
        session = await db.get_session(character_session_id)
        if session:
            return session

    if guild_id and channel_id and hasattr(db, 'get_session_by_channel'):
        session = await db.get_session_by_channel(guild_id, channel_id, statuses=statuses)
        if session:
            return session

    if guild_id and user_id and hasattr(db, 'get_user_active_session'):
        session = await db.get_user_active_session(guild_id, user_id)
        if session and session.get('status') in statuses:
            return session

    if guild_id and hasattr(db, 'get_active_session'):
        session = await db.get_active_session(guild_id)
        if session:
            return session

    return None


async def load_runtime_content(
    db,
    filename: str,
    *,
    guild_id: Optional[int] = None,
    user_id: Optional[int] = None,
    channel_id: Optional[int] = None,
    session_id: Optional[int] = None,
    character: Optional[Dict[str, Any]] = None,
    statuses: Optional[list[str]] = None,
):
    """Load a content-pack scoped file for the best available runtime session."""
    session = await resolve_runtime_session(
        db,
        guild_id=guild_id,
        user_id=user_id,
        channel_id=channel_id,
        session_id=session_id,
        character=character,
        statuses=statuses,
    )
    return load_session_content_file(session, filename)
