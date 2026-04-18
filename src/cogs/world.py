"""
RPG DM Bot - World management cog.
Thin DM/admin controls for campaign state during active play.
"""

import json
import logging
from typing import Any, Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands


logger = logging.getLogger('rpg.world')


class World(commands.Cog):
    """DM-facing world management commands."""

    world_group = app_commands.Group(
        name="world",
        description="Manage live world state for the active session",
        guild_only=True,
    )

    def __init__(self, bot):
        self.bot = bot

    @property
    def db(self):
        return self.bot.db

    @property
    def tools(self):
        return self.bot.tools

    async def _resolve_session(self, interaction: discord.Interaction) -> Optional[Dict[str, Any]]:
        persistence = self.bot.get_cog('GamePersistence')
        if persistence and hasattr(persistence, '_resolve_context_session'):
            return await persistence._resolve_context_session(
                interaction.guild.id,
                interaction.channel.id,
                interaction.user.id,
                statuses=['active', 'paused', 'inactive'],
            )
        return None

    async def _require_dm_or_admin(self, interaction: discord.Interaction, session: Dict[str, Any]) -> bool:
        if session.get('dm_user_id') == interaction.user.id:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            'Only the session DM or a server administrator can use this command.',
            ephemeral=True,
        )
        return False

    @world_group.command(name="scene-set", description="Set the session's current scene note")
    @app_commands.describe(description="Current scene summary for the DM and browser clients")
    async def scene_set(self, interaction: discord.Interaction, description: str):
        session = await self._resolve_session(interaction)
        if not session:
            await interaction.response.send_message('No session is active for this channel.', ephemeral=True)
            return
        if not await self._require_dm_or_admin(interaction, session):
            return

        await self.db.save_game_state(
            session['id'],
            current_scene=description,
            active_content_pack_id=session.get('content_pack_id'),
        )
        await interaction.response.send_message(f"Scene updated for **{session['name']}**.", ephemeral=True)

    @world_group.command(name="location-move", description="Move the party to a location")
    @app_commands.describe(location="Exact location name in the current session", travel_description="Optional travel note")
    async def location_move(self, interaction: discord.Interaction, location: str, travel_description: Optional[str] = None):
        session = await self._resolve_session(interaction)
        if not session:
            await interaction.response.send_message('No session is active for this channel.', ephemeral=True)
            return
        if not await self._require_dm_or_admin(interaction, session):
            return

        target = await self.db.get_location_by_name(session['id'], location)
        if not target:
            await interaction.response.send_message(f"Location '{location}' was not found in this session.", ephemeral=True)
            return

        result_text = await self.tools._move_party_to_location(
            {
                'guild_id': interaction.guild.id,
                'channel_id': interaction.channel.id,
                'user_id': interaction.user.id,
                'session_id': session['id'],
            },
            {
                'location_id': target['id'],
                'travel_description': travel_description or '',
            },
        )
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            result = {'success': False, 'reason': 'tool_error', 'message': result_text}

        if not result.get('success'):
            await interaction.response.send_message(result.get('message') or f"Could not move party: {result.get('reason', 'unknown error')}", ephemeral=True)
            return

        await interaction.response.send_message(result.get('narration') or f"Party moved to **{target['name']}**.")

    @world_group.command(name="location-reveal", description="Reveal a hidden location to players")
    @app_commands.describe(location="Exact location name in the current session")
    async def location_reveal(self, interaction: discord.Interaction, location: str):
        session = await self._resolve_session(interaction)
        if not session:
            await interaction.response.send_message('No session is active for this channel.', ephemeral=True)
            return
        if not await self._require_dm_or_admin(interaction, session):
            return

        target = await self.db.get_location_by_name(session['id'], location)
        if not target:
            await interaction.response.send_message(f"Location '{location}' was not found in this session.", ephemeral=True)
            return

        await self.db.reveal_location(target['id'])
        await interaction.response.send_message(f"Revealed location **{target['name']}**.", ephemeral=True)

    @world_group.command(name="npc-reveal", description="Mark an NPC as encountered and visible to players")
    @app_commands.describe(npc="Exact NPC name in the current session")
    async def npc_reveal(self, interaction: discord.Interaction, npc: str):
        session = await self._resolve_session(interaction)
        if not session:
            await interaction.response.send_message('No session is active for this channel.', ephemeral=True)
            return
        if not await self._require_dm_or_admin(interaction, session):
            return

        target = await self.db.get_npc_by_name(session['id'], npc)
        if not target:
            await interaction.response.send_message(f"NPC '{npc}' was not found in this session.", ephemeral=True)
            return

        await self.db.reveal_npc(target['id'])
        await interaction.response.send_message(f"Revealed NPC **{target['name']}**.", ephemeral=True)

    @world_group.command(name="faction-rep", description="Adjust a character's reputation with a faction")
    @app_commands.describe(faction="Faction name", character="Character name", change="Signed reputation change", notes="Optional note")
    async def faction_rep(self, interaction: discord.Interaction, faction: str, character: str, change: int, notes: Optional[str] = None):
        session = await self._resolve_session(interaction)
        if not session:
            await interaction.response.send_message('No session is active for this channel.', ephemeral=True)
            return
        if not await self._require_dm_or_admin(interaction, session):
            return

        faction_record = await self.db.get_faction_by_name(session['id'], faction)
        if not faction_record:
            await interaction.response.send_message(f"Faction '{faction}' was not found in this session.", ephemeral=True)
            return

        characters = await self.db.get_session_characters(session['id'])
        target_character = next((entry for entry in characters if str(entry.get('name', '')).lower() == character.lower()), None)
        if not target_character:
            await interaction.response.send_message(f"Character '{character}' was not found in this session.", ephemeral=True)
            return

        new_reputation = await self.db.update_character_faction_reputation(
            target_character['id'],
            faction_record['id'],
            reputation_change=change,
            notes=notes,
        )
        await interaction.response.send_message(
            f"{target_character['name']}'s reputation with **{faction_record['name']}** is now **{new_reputation}**.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(World(bot))
