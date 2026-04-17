"""Shared utility helpers."""


def get_character_class(character: dict, default: str = "Unknown") -> str:
    """Return the normalized character class field used across older/newer rows."""
    return character.get('char_class') or character.get('class') or default


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
