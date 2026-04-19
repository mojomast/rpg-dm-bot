"""
RPG DM Bot - Game Persistence Cog
Handles game/quest persistence between sessions, story logging, and game state management.
Ensures games can be resumed with full context after breaks.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

logger = logging.getLogger('rpg.game_persistence')


class GamePersistence(commands.Cog):
    """Manages game persistence, story logs, and session resumption"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    @property
    def llm(self):
        return self.bot.llm

    async def _resolve_game_state_location(self, session_id: int, game_state: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Resolve the authoritative session location, falling back to legacy text when needed."""
        if not game_state:
            return None

        location_id = game_state.get('current_location_id')
        if location_id:
            location = await self.db.get_location(location_id)
            if location:
                return location

        location_name = game_state.get('current_location')
        if not location_name:
            return None

        locations = await self.db.get_locations(session_id=session_id)
        return next((loc for loc in locations if loc.get('name') == location_name), None)

    async def _get_guild_session(self, guild_id: int, session_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a session only if it belongs to the current guild."""
        session = await self.db.get_session(session_id)
        if not session or session.get('guild_id') != guild_id:
            return None
        return session

    async def _resolve_context_session(
        self,
        guild_id: int,
        channel_id: Optional[int] = None,
        user_id: Optional[int] = None,
        statuses: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Resolve the most relevant session for the current guild/channel/user context."""
        statuses = statuses or ['active']
        get_session_by_channel = getattr(self.db, 'get_session_by_channel', None)
        get_user_active_session = getattr(self.db, 'get_user_active_session', None)

        if channel_id and get_session_by_channel:
            session = await get_session_by_channel(guild_id, channel_id, statuses=statuses)
            if session:
                return session

        if user_id and get_user_active_session:
            user_session = await get_user_active_session(guild_id, user_id)
            if user_session and user_session.get('status') in statuses:
                return user_session

        for status in statuses:
            sessions = await self.db.get_sessions(guild_id, status=status)
            if sessions:
                return sessions[0]

        return None
    
    # =========================================================================
    # STORY LOG COMMANDS
    # =========================================================================
    
    story_group = app_commands.Group(
        name="story",
        description="Story and game history commands",
        guild_only=True
    )
    
    @story_group.command(name="log", description="Add an important event to the story log")
    @app_commands.describe(
        event="Description of what happened",
        event_type="Type of event"
    )
    @app_commands.choices(event_type=[
        app_commands.Choice(name="🗡️ Combat", value="combat"),
        app_commands.Choice(name="💬 Dialogue", value="dialogue"),
        app_commands.Choice(name="🔍 Discovery", value="discovery"),
        app_commands.Choice(name="🎯 Quest", value="quest"),
        app_commands.Choice(name="📍 Location", value="location"),
        app_commands.Choice(name="📝 Note", value="note"),
    ])
    async def add_story_log(
        self,
        interaction: discord.Interaction,
        event: str,
        event_type: str = "note"
    ):
        """Add an event to the story log"""
        session = await self._resolve_context_session(
            interaction.guild.id,
            interaction.channel.id,
            interaction.user.id,
            statuses=['active'],
        )
        if not session:
            await interaction.response.send_message(
                "❌ No active game session! Start one with `/game start`",
                ephemeral=True
            )
            return
        
        # Get the user's character for participant info
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        participants = [char['name']] if char else [interaction.user.display_name]
        
        # Log the event
        await self.db.add_story_entry(
            session_id=session['id'],
            entry_type=event_type,
            content=event,
            participants=participants
        )
        
        type_emojis = {
            'combat': '🗡️',
            'dialogue': '💬',
            'discovery': '🔍',
            'quest': '🎯',
            'location': '📍',
            'note': '📝'
        }
        
        await interaction.response.send_message(
            f"{type_emojis.get(event_type, '📝')} Story logged: *{event[:100]}{'...' if len(event) > 100 else ''}*",
            ephemeral=True
        )
    
    @story_group.command(name="recap", description="Get a recap of recent events")
    @app_commands.describe(count="Number of recent events to show (default: 10)")
    async def story_recap(self, interaction: discord.Interaction, count: int = 10):
        """Show recent story events"""
        session = await self._resolve_context_session(
            interaction.guild.id,
            interaction.channel.id,
            interaction.user.id,
            statuses=['active', 'paused', 'inactive'],
        )
        if not session:
            await interaction.response.send_message(
                "❌ No game sessions found!",
                ephemeral=True
            )
            return
        entries = await self.db.get_story_log(session['id'], limit=count)
        
        if not entries:
            await interaction.response.send_message(
                "📜 No story entries yet. Events will be logged as you play!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📜 Story Recap: {session['name']}",
            description=f"Last {len(entries)} events:",
            color=discord.Color.gold()
        )
        
        type_emojis = {
            'combat': '🗡️',
            'dialogue': '💬',
            'discovery': '🔍',
            'quest': '🎯',
            'location': '📍',
            'note': '📝'
        }
        
        for entry in reversed(entries):  # Show oldest first
            emoji = type_emojis.get(entry['entry_type'], '📝')
            timestamp = entry['created_at'][:10] if entry.get('created_at') else 'Unknown'
            
            # Truncate long entries
            content = entry['content'][:200] + '...' if len(entry['content']) > 200 else entry['content']
            
            embed.add_field(
                name=f"{emoji} {entry['entry_type'].title()} ({timestamp})",
                value=content,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @story_group.command(name="summary", description="Get an AI-generated summary of the adventure so far")
    async def story_summary(self, interaction: discord.Interaction):
        """Generate an AI summary of the story"""
        await interaction.response.defer()

        session = await self._resolve_context_session(
            interaction.guild.id,
            interaction.channel.id,
            interaction.user.id,
            statuses=['active', 'paused', 'inactive'],
        )
        if not session:
            await interaction.followup.send("❌ No game sessions found!", ephemeral=True)
            return
        entries = await self.db.get_story_log(session['id'], limit=50)
        
        if not entries:
            await interaction.followup.send(
                "📜 No story to summarize yet. Play some more!",
                ephemeral=True
            )
            return
        
        # Get party info
        players = await self.db.get_session_players(session['id'])
        party_info = []
        for p in players:
            # Skip players without a character assigned
            if not p.get('character_id'):
                continue
            char = await self.db.get_character(p['character_id'])
            if char:
                party_info.append(char)
        
        # Build context for summary
        story_text = "\n".join([
            f"[{e['entry_type']}] {e['content']}"
            for e in entries
        ])
        
        party_text = "\n".join([
            f"- {c['name']}: Level {c['level']} {c['race']} {c['char_class']}"
            for c in party_info
        ])
        
        if self.llm:
            try:
                summary_prompt = f"""Summarize this RPG adventure so far. Be dramatic and engaging!

ADVENTURE: {session['name']}
DESCRIPTION: {session.get('description', 'An epic quest')}

PARTY:
{party_text}

STORY EVENTS:
{story_text}

Write a 2-3 paragraph summary of the adventure's key events and current situation.
Make it feel like a "Previously on..." recap that gets players excited to continue."""

                response = await self.llm.chat(
                    messages=[
                        {"role": "system", "content": "You are a dramatic narrator summarizing an RPG adventure."},
                        {"role": "user", "content": summary_prompt}
                    ],
                    max_tokens=15000
                )
                
                summary = response if isinstance(response, str) else "Failed to generate summary."
            except Exception as e:
                logger.error(f"Error generating summary: {e}")
                summary = "Unable to generate AI summary. Check the story recap instead!"
        else:
            summary = "AI summarization unavailable. Use `/story recap` to see recent events."
        
        embed = discord.Embed(
            title=f"📖 The Story So Far: {session['name']}",
            description=summary,
            color=discord.Color.purple()
        )
        embed.set_footer(text="Use /story recap for detailed event log")
        
        await interaction.followup.send(embed=embed)
    
    # =========================================================================
    # GAME STATE COMMANDS
    # =========================================================================

    @app_commands.command(name="debug_gamestate", description="Admin-only debug dump for the current game state")
    @app_commands.guild_only()
    async def debug_gamestate(self, interaction: discord.Interaction):
        """Show a compact admin-only snapshot of session, combat, and inventory state."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            session = await self._resolve_context_session(
                interaction.guild.id,
                interaction.channel.id,
                interaction.user.id,
                statuses=['active', 'paused', 'inactive'],
            )

            if not session:
                await interaction.followup.send("No session found for this context.", ephemeral=True)
                return

            game_state = await self.db.get_game_state(session['id'])
            combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
            combatants = await self.db.get_combat_participants(combat['id']) if combat else []
            players = await self.db.get_session_players(session['id'])

            lines = [
                f"Session: {session['name']} (id={session['id']}, status={session.get('status')})",
                f"Channel: {interaction.channel.id}",
            ]

            if game_state:
                lines.append(
                    f"GameState: location={game_state.get('current_location')!r} location_id={game_state.get('current_location_id')} scene={game_state.get('current_scene')!r} turn_count={game_state.get('turn_count')}"
                )
            else:
                lines.append("GameState: none")

            if combat:
                lines.append(
                    f"Combat: id={combat['id']} round={combat.get('round_number')} current_turn={combat.get('current_turn')} initiative_order={combat.get('initiative_order')}"
                )
                for combatant in combatants:
                    lines.append(
                        f"- Combatant id={combatant['id']} name={combatant['name']} hp={combatant['current_hp']}/{combatant['max_hp']} player={combatant.get('is_player')} type={combatant.get('participant_type')} participant_id={combatant.get('participant_id')} turn_order={combatant.get('turn_order')}"
                    )
            else:
                lines.append("Combat: none")

            if players:
                lines.append("Players:")
                for player in players:
                    char = await self.db.get_character(player['character_id']) if player.get('character_id') else None
                    if char:
                        inventory = await self.db.get_inventory(char['id'])
                        lines.append(
                            f"- user_id={player['user_id']} character={char['name']} char_id={char['id']} gold={char.get('gold')} inventory_count={len(inventory)}"
                        )
                    else:
                        lines.append(f"- user_id={player['user_id']} character=None")

            await interaction.followup.send(f"```text\n" + "\n".join(lines[:80]) + "\n```", ephemeral=True)
        except Exception as exc:
            logger.error("Failed to build debug gamestate: %s", exc, exc_info=True)
            await interaction.followup.send("❌ Failed to build debug gamestate.", ephemeral=True)
    
    @app_commands.command(name="resume", description="Resume a paused or previous game session")
    @app_commands.describe(session_id="The session ID to resume (optional - uses most recent)")
    @app_commands.guild_only()
    async def resume_game(self, interaction: discord.Interaction, session_id: Optional[int] = None):
        """Resume a game with full context restoration"""
        sessions_cog = self.bot.get_cog('Sessions')
        target_session_id = session_id

        if target_session_id:
            session = await self._get_guild_session(interaction.guild.id, target_session_id)
            if not session:
                await interaction.response.send_message("❌ Game not found!", ephemeral=True)
                return
        else:
            # Get most recent session
            session = await self._resolve_context_session(
                interaction.guild.id,
                interaction.channel.id,
                interaction.user.id,
                statuses=['paused', 'inactive'],
            )

            if not session:
                await interaction.response.send_message(
                    "❌ No games to resume! Start one with `/game start`",
                    ephemeral=True
                )
                return

            target_session_id = session['id']

        if sessions_cog:
            return await sessions_cog.resume_session.callback(sessions_cog, interaction, target_session_id)

        await interaction.response.defer()
        
        # Check permissions
        if session['dm_user_id'] != interaction.user.id:
            await interaction.followup.send(
                "❌ Only the game creator can resume this session!",
                ephemeral=True
            )
            return
        
        # Get game state
        game_state = await self.db.get_game_state(session['id'])
        
        # Get party info
        players = await self.db.get_session_players(session['id'])
        party_info = []
        for p in players:
            # Skip players without a character assigned
            if not p.get('character_id'):
                continue
            char = await self.db.get_character(p['character_id'])
            if char:
                party_info.append(char)
        
        # Get recent story
        story_entries = await self.db.get_story_log(session['id'], limit=10)
        current_location = await self._resolve_game_state_location(session['id'], game_state)
        
        # Mark session as active
        await self.db.update_session(session['id'], status='active')
        
        # Build resume context
        party_text = "\n".join([
            f"• **{c['name']}** - Level {c['level']} {c['race']} {c['char_class']} ({c['hp']}/{c['max_hp']} HP)"
            for c in party_info
        ])
        
        # Generate AI recap if available
        if self.llm and story_entries:
            try:
                story_text = "\n".join([e['content'] for e in story_entries[-5:]])
                
                recap_prompt = f"""The adventurers are resuming their game. Give a brief "when we last left off" recap.

ADVENTURE: {session['name']}
{session.get('description', '')}

PARTY:
{party_text}

RECENT EVENTS:
{story_text}

CURRENT SCENE: {game_state.get('current_scene', 'Unknown') if game_state else 'Unknown'}
LOCATION: {current_location.get('name', 'Unknown') if current_location else (game_state.get('current_location', 'Unknown') if game_state else 'Unknown')}

Write 2-3 sentences reminding them where they were and what was happening, then ask "What do you do?" """

                response = await self.llm.chat(
                    messages=[
                        {"role": "system", "content": self.bot.prompts.get_dm_system_prompt()},
                        {"role": "user", "content": recap_prompt}
                    ],
                    max_tokens=15000
                )
                
                recap = response if isinstance(response, str) else ""
            except Exception as e:
                logger.error(f"Error generating recap: {e}")
                recap = ""
        else:
            recap = ""
        
        embed = discord.Embed(
            title=f"▶️ Resuming: {session['name']}",
            description=recap or f"*Welcome back to **{session['name']}**!*\n\n{session.get('description', 'Your adventure continues...')}",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🎭 Party",
            value=party_text or "No players yet",
            inline=False
        )
        
        if game_state:
            if current_location or game_state.get('current_location'):
                embed.add_field(
                    name="📍 Location",
                    value=current_location.get('name') if current_location else game_state['current_location'],
                    inline=True
                )
            if game_state.get('turn_count'):
                embed.add_field(
                    name="⏱️ Turns",
                    value=str(game_state['turn_count']),
                    inline=True
                )
        
        embed.set_footer(text="@mention the bot or use /dm to continue your adventure!")
        
        await interaction.followup.send(embed=embed)
        
        # Log the resume
        await self.db.add_story_entry(
            session_id=session['id'],
            entry_type='note',
            content=f"Session resumed by {interaction.user.display_name}",
            participants=[interaction.user.display_name]
        )
    
    @app_commands.command(name="save", description="Save the current game state")
    @app_commands.describe(
        note="Optional note about what's happening",
        location="Current location name"
    )
    @app_commands.guild_only()
    async def save_game(
        self,
        interaction: discord.Interaction,
        note: Optional[str] = None,
        location: Optional[str] = None
    ):
        """Manually save the current game state"""
        session = await self._resolve_context_session(
            interaction.guild.id,
            interaction.channel.id,
            interaction.user.id,
            statuses=['active'],
        )
        if not session:
            await interaction.response.send_message(
                "❌ No active game to save!",
                ephemeral=True
            )
            return
        
        # Get current party state
        players = await self.db.get_session_players(session['id'])
        party_data = []
        for p in players:
            # Skip players without a character assigned
            if not p.get('character_id'):
                continue
            char = await self.db.get_character(p['character_id'])
            if char:
                party_data.append({
                    'name': char['name'],
                    'race': char['race'],
                    'char_class': char['char_class'],
                    'level': char['level'],
                    'hp': char['hp'],
                    'max_hp': char['max_hp'],
                    'backstory': char.get('backstory')
                })
        
        # Save state
        existing_state = await self.db.get_game_state(session['id']) or {}
        current_location = await self._resolve_game_state_location(session['id'], existing_state)
        resolved_location = current_location
        if location:
            locations = await self.db.get_locations(session_id=session['id'])
            resolved_location = next((loc for loc in locations if loc.get('name', '').lower() == location.lower()), None)

        await self.db.save_game_state(
            session_id=session['id'],
            current_location=resolved_location.get('name') if resolved_location else (location or existing_state.get('current_location')),
            current_location_id=resolved_location.get('id') if resolved_location else existing_state.get('current_location_id'),
            dm_notes=note,
            game_data={
                'party_snapshot': party_data,
                'saved_at': datetime.utcnow().isoformat(),
                'saved_by': interaction.user.display_name
            }
        )
        
        # Log the save
        if note:
            await self.db.add_story_entry(
                session_id=session['id'],
                entry_type='note',
                content=f"Game saved: {note}",
                participants=[interaction.user.display_name]
            )
        
        await interaction.response.send_message(
            f"💾 Game saved! {f'Note: {note}' if note else ''}",
            ephemeral=True
        )
    
    # =========================================================================
    # ACTIVE QUEST COMMANDS (renamed to avoid conflict with quests cog)
    # =========================================================================
    
    activequest_group = app_commands.Group(
        name="activequest",
        description="View current quest status and progress",
        guild_only=True
    )
    
    @activequest_group.command(name="current", description="View the current active quest")
    async def current_quest(self, interaction: discord.Interaction):
        """Show current quest details"""
        session = await self._resolve_context_session(
            interaction.guild.id,
            interaction.channel.id,
            interaction.user.id,
            statuses=['active'],
        )
        if not session:
            await interaction.response.send_message(
                "❌ No active game session!",
                ephemeral=True
            )
            return
        
        if not session.get('current_quest_id'):
            await interaction.response.send_message(
                "📜 No active quest. The adventure awaits!",
                ephemeral=True
            )
            return
        
        quest = await self.db.get_quest(session['current_quest_id'])
        if not quest:
            await interaction.response.send_message(
                "❌ Quest data not found!",
                ephemeral=True
            )
            return
        
        # Get objectives
        objectives = json.loads(quest.get('objectives', '[]')) if isinstance(quest.get('objectives'), str) else quest.get('objectives', [])
        
        embed = discord.Embed(
            title=f"📜 {quest['title']}",
            description=quest.get('description', 'No description'),
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="⚔️ Difficulty",
            value=quest.get('difficulty', 'Unknown').title(),
            inline=True
        )
        
        embed.add_field(
            name="📊 Status",
            value=quest.get('status', 'active').title(),
            inline=True
        )
        
        if objectives:
            obj_text = "\n".join([
                f"{'✅' if obj.get('completed') else '⬜'} {obj.get('description', 'Unknown')}"
                for obj in objectives
            ])
            embed.add_field(
                name="🎯 Objectives",
                value=obj_text[:1024] or "No objectives",
                inline=False
            )
        
        # Get rewards
        rewards = json.loads(quest.get('rewards', '{}')) if isinstance(quest.get('rewards'), str) else quest.get('rewards', {})
        if rewards:
            reward_text = []
            if rewards.get('gold'):
                reward_text.append(f"💰 {rewards['gold']} gold")
            if rewards.get('xp'):
                reward_text.append(f"✨ {rewards['xp']} XP")
            if rewards.get('items'):
                reward_text.append(f"🎁 Items: {', '.join(rewards['items'])}")
            
            if reward_text:
                embed.add_field(
                    name="🏆 Rewards",
                    value="\n".join(reward_text),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    
    @activequest_group.command(name="list", description="List all quests for this game")
    async def list_quests(self, interaction: discord.Interaction):
        """List all quests"""
        session = await self._resolve_context_session(
            interaction.guild.id,
            interaction.channel.id,
            interaction.user.id,
            statuses=['active', 'paused', 'inactive'],
        )
        if not session:
            await interaction.response.send_message(
                "❌ No game sessions found!",
                ephemeral=True
            )
            return

        quests = await self.db.get_quests(session_id=session['id'])
        
        if not quests:
            await interaction.response.send_message(
                "📜 No quests yet! Explore and talk to NPCs to find adventures.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📜 Quests: {session['name']}",
            color=discord.Color.blue()
        )
        
        status_emojis = {
            'available': '🆕',
            'active': '🔥',
            'completed': '✅',
            'failed': '❌'
        }
        
        for quest in quests[:10]:
            emoji = status_emojis.get(quest['status'], '📜')
            objectives = json.loads(quest.get('objectives', '[]')) if isinstance(quest.get('objectives'), str) else quest.get('objectives', [])
            completed = sum(1 for o in objectives if o.get('completed'))
            
            embed.add_field(
                name=f"{emoji} {quest['title']}",
                value=f"{quest.get('description', 'No description')[:100]}...\n"
                      f"*Difficulty: {quest.get('difficulty', 'Unknown')} | Progress: {completed}/{len(objectives)}*",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    # =========================================================================
    # AUTO-LOGGING LISTENERS
    # =========================================================================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Auto-log significant game events from DM responses"""
        # Only process bot's own messages in guild channels
        if message.author.id != self.bot.user.id:
            return
        
        if not message.guild:
            return
        
        session = await self._resolve_context_session(
            message.guild.id,
            message.channel.id,
            None,
            statuses=['active'],
        )
        if not session:
            return
        
        # Check for combat-related keywords to auto-log
        content_lower = message.content.lower()
        
        # Auto-log combat events
        if any(word in content_lower for word in ['deals damage', 'takes damage', 'hits', 'misses', 'attacks', 'defeated', 'slain']):
            await self.db.add_story_entry(
                session_id=session['id'],
                entry_type='combat',
                content=message.content[:500],
                participants=[]
            )
        
        # Auto-log discoveries
        elif any(word in content_lower for word in ['discover', 'find', 'uncover', 'reveal', 'learn']):
            await self.db.add_story_entry(
                session_id=session['id'],
                entry_type='discovery',
                content=message.content[:500],
                participants=[]
            )
        
        # Auto-log location changes
        elif any(word in content_lower for word in ['arrive at', 'enter', 'reach', 'come to']):
            await self.db.add_story_entry(
                session_id=session['id'],
                entry_type='location',
                content=message.content[:500],
                participants=[]
            )


async def setup(bot):
    await bot.add_cog(GamePersistence(bot))
