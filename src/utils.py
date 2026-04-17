"""Shared utility helpers."""


async def send_chunked(target, content: str, view=None, max_len: int = 2000):
    """Send long text content in Discord-sized chunks."""
    chunks = [content[i:i + max_len] for i in range(0, len(content), max_len)] or [""]
    for index, chunk in enumerate(chunks):
        kwargs = {'view': view} if view and index == len(chunks) - 1 else {}
        await target.send(chunk, **kwargs)
