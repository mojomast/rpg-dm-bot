"""
RPG DM Bot - DM Chat Cog
Handles AI Dungeon Master interactions with tool execution
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord import ui
import logging
import json
import asyncio
import re
from typing import Optional, Dict, List
from datetime import datetime

from src.chat_handler import ChatActor, ChatHandler
from src.mechanics_tracker import new_tracker, get_tracker
from src.utils import send_chunked

logger = logging.getLogger('rpg.dm_chat')

# Maximum tool execution rounds
MAX_TOOL_ROUNDS = 5

# Message batching delay (seconds) - wait for multiple players before responding
MESSAGE_BATCH_DELAY = 3.0

# Import proactive DM guidelines
from src.prompts import PROACTIVE_DM_GUIDELINES


# ============================================================================
# DISCORD UI COMPONENTS
# ============================================================================

class PlayerActionButton(ui.Button):
    """A button for quick player actions"""
    
    def __init__(self, label: str, action: str, style: discord.ButtonStyle = discord.ButtonStyle.primary, emoji: str = None):
        super().__init__(label=label, style=style, emoji=emoji, custom_id=f"action_{action}")
        self.action = action
    
    async def callback(self, interaction: discord.Interaction):
        # Defer to show we're processing
        await interaction.response.defer()
        
        # Get the cog to process the action
        cog = interaction.client.get_cog('DMChat')
        if not cog:
            await interaction.followup.send("Error: DM not available", ephemeral=True)
            return
        
        # Get character
        char = await cog.db.get_active_character(interaction.user.id, interaction.guild.id)
        if not char:
            await interaction.followup.send("❌ You need a character first! Use `/game menu`", ephemeral=True)
            return
        
        # Build the action prompt
        action_prompts = {
            'look': f"{char['name']} looks around carefully.",
            'continue': f"{char['name']} continues forward.",
        }
        if self.action.startswith('option_'):
            option_text = self.label
            prompt = f"{char['name']} chooses: {option_text}"
        else:
            prompt = action_prompts.get(self.action, f"{char['name']} does: {self.action}")

        response, mechanics_text = await cog.process_dm_input(
            channel=interaction.channel,
            guild=interaction.guild,
            author=interaction.user,
            user_message=prompt,
        )

        full_response = cog.build_full_response(response, mechanics_text)
        view = GameActionsView(cog, options=cog.extract_response_options(response))
        await send_chunked(interaction.followup, full_response, view=view)


class InfoButton(ui.Button):
    """A button for viewing game info (character sheet, quest, etc)"""
    
    def __init__(self, label: str, info_type: str, style: discord.ButtonStyle = discord.ButtonStyle.secondary, emoji: str = None):
        super().__init__(label=label, style=style, emoji=emoji, custom_id=f"info_{info_type}")
        self.info_type = info_type
    
    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog('DMChat')
        if not cog:
            await interaction.response.send_message("Error: DM not available", ephemeral=True)
            return
        
        if self.info_type == 'character':
            await self._show_character_sheet(interaction, cog)
        elif self.info_type == 'quest':
            await self._show_quest_info(interaction, cog)
        elif self.info_type == 'location':
            await self._show_location_info(interaction, cog)
        elif self.info_type == 'inventory':
            await self._show_inventory(interaction, cog)
        elif self.info_type == 'party':
            await self._show_party_info(interaction, cog)
    
    async def _show_character_sheet(self, interaction: discord.Interaction, cog):
        char = await cog.db.get_active_character(interaction.user.id, interaction.guild.id)
        if not char:
            await interaction.response.send_message("❌ No character found!", ephemeral=True)
            return
        
        char_class = char.get('char_class') or char.get('class', 'Unknown')
        
        embed = discord.Embed(
            title=f"📜 {char['name']}",
            description=char.get('backstory', '*No backstory yet*')[:200],
            color=discord.Color.gold()
        )
        embed.add_field(
            name="⚔️ Class & Race",
            value=f"Level {char['level']} {char['race']} {char_class}",
            inline=False
        )
        embed.add_field(
            name="❤️ Health",
            value=f"{char['hp']}/{char['max_hp']} HP",
            inline=True
        )
        embed.add_field(
            name="✨ Mana",
            value=f"{char.get('mana', 0)}/{char.get('max_mana', 0)}",
            inline=True
        )
        embed.add_field(
            name="💰 Gold",
            value=str(char['gold']),
            inline=True
        )
        embed.add_field(
            name="📊 Stats",
            value=(
                f"**STR** {char['strength']} | **DEX** {char['dexterity']} | **CON** {char['constitution']}\n"
                f"**INT** {char['intelligence']} | **WIS** {char['wisdom']} | **CHA** {char['charisma']}"
            ),
            inline=False
        )
        embed.add_field(
            name="⭐ Experience",
            value=f"{char.get('xp', char.get('experience', 0))} XP",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _show_quest_info(self, interaction: discord.Interaction, cog):
        session = await cog.resolve_session(interaction.guild.id, interaction.user.id, interaction.channel.id)
        if not session or not session.get('current_quest_id'):
            await interaction.response.send_message("📋 No active quest!", ephemeral=True)
            return
        
        quest = await cog.db.get_quest(session['current_quest_id'])
        if not quest:
            await interaction.response.send_message("📋 Quest not found!", ephemeral=True)
            return
        
        stages = await cog.db.get_quest_stages(quest['id'])
        current_stage = stages[quest['current_stage']] if quest['current_stage'] < len(stages) else None
        
        embed = discord.Embed(
            title=f"📜 {quest['title']}",
            description=quest['description'],
            color=discord.Color.blue()
        )
        embed.add_field(
            name="⚔️ Difficulty",
            value=quest['difficulty'].title(),
            inline=True
        )
        embed.add_field(
            name="📊 Progress",
            value=f"Stage {quest['current_stage'] + 1}/{len(stages)}",
            inline=True
        )
        
        if current_stage:
            embed.add_field(
                name=f"🎯 Current: {current_stage['title']}",
                value=current_stage['description'][:200],
                inline=False
            )
        
        if quest.get('rewards'):
            rewards = quest['rewards']
            reward_text = []
            if rewards.get('gold'):
                reward_text.append(f"💰 {rewards['gold']} gold")
            if rewards.get('xp'):
                reward_text.append(f"⭐ {rewards['xp']} XP")
            if rewards.get('items'):
                reward_text.append(f"📦 {len(rewards['items'])} items")
            if reward_text:
                embed.add_field(name="🎁 Rewards", value="\n".join(reward_text), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _show_location_info(self, interaction: discord.Interaction, cog):
        session = await cog.resolve_session(interaction.guild.id, interaction.user.id, interaction.channel.id)
        if not session:
            await interaction.response.send_message("🗺️ No active session!", ephemeral=True)
            return
        
        game_state = await cog.db.get_game_state(session['id'])
        if not game_state or not game_state.get('current_location_id'):
            loc_name = game_state.get('current_location', 'Unknown') if game_state else 'Unknown'
            await interaction.response.send_message(f"🗺️ Current location: **{loc_name}**", ephemeral=True)
            return
        
        location = await cog.db.get_location(game_state['current_location_id'])
        if not location:
            await interaction.response.send_message("🗺️ Location not found!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🗺️ {location['name']}",
            description=location.get('description', '*No description*'),
            color=discord.Color.green()
        )
        
        if location.get('location_type'):
            embed.add_field(name="Type", value=location['location_type'].title(), inline=True)
        
        if location.get('danger_level', 0) > 0:
            danger = location['danger_level']
            danger_text = "⚪ Safe" if danger < 2 else "🟢 Low" if danger < 4 else "🟡 Moderate" if danger < 6 else "🟠 High" if danger < 8 else "🔴 Deadly"
            embed.add_field(name="Danger", value=danger_text, inline=True)
        
        if location.get('current_weather'):
            embed.add_field(name="🌤️ Weather", value=location['current_weather'], inline=True)
        
        # Get nearby locations
        nearby = await cog.db.get_nearby_locations(location['id'])
        if nearby:
            exits = []
            for loc in nearby[:5]:
                direction = f" ({loc.get('direction')})" if loc.get('direction') else ""
                exits.append(f"• {loc.get('to_name', 'Unknown')}{direction}")
            embed.add_field(name="🚪 Exits", value="\n".join(exits), inline=False)
        
        # Get NPCs at location
        npcs = await cog.db.get_npcs_at_location(location['id'])
        if npcs:
            npc_list = [f"• {npc['name']}" + (" 🛒" if npc.get('is_merchant') else "") for npc in npcs[:5]]
            embed.add_field(name="👥 NPCs Here", value="\n".join(npc_list), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _show_inventory(self, interaction: discord.Interaction, cog):
        char = await cog.db.get_active_character(interaction.user.id, interaction.guild.id)
        if not char:
            await interaction.response.send_message("❌ No character found!", ephemeral=True)
            return
        
        inventory = await cog.db.get_inventory(char['id'])
        
        embed = discord.Embed(
            title=f"🎒 {char['name']}'s Inventory",
            color=discord.Color.orange()
        )
        embed.add_field(name="💰 Gold", value=str(char['gold']), inline=True)
        
        if inventory:
            items_text = []
            for item in inventory[:15]:
                qty = f" ×{item['quantity']}" if item.get('quantity', 1) > 1 else ""
                equipped = " ⚔️" if item.get('is_equipped') else ""
                items_text.append(f"• {item['item_name']}{qty}{equipped}")
            embed.add_field(name="📦 Items", value="\n".join(items_text) or "Empty", inline=False)
        else:
            embed.add_field(name="📦 Items", value="*Your pack is empty*", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _show_party_info(self, interaction: discord.Interaction, cog):
        session = await cog.resolve_session(interaction.guild.id, interaction.user.id, interaction.channel.id)
        if not session:
            await interaction.response.send_message("👥 No active session!", ephemeral=True)
            return
        
        players = await cog.db.get_session_players(session['id'])
        
        embed = discord.Embed(
            title=f"👥 Party - {session['name']}",
            color=discord.Color.purple()
        )
        
        if players:
            for p in players:
                if not p.get('character_id'):
                    continue
                char = await cog.db.get_character(p['character_id'])
                if char:
                    char_class = char.get('char_class') or char.get('class', '?')
                    hp_bar = "❤️" * min(5, char['hp'] * 5 // max(1, char['max_hp'])) + "🖤" * (5 - min(5, char['hp'] * 5 // max(1, char['max_hp'])))
                    embed.add_field(
                        name=f"{char['name']} - Lv{char['level']} {char['race']} {char_class}",
                        value=f"{hp_bar} {char['hp']}/{char['max_hp']} HP",
                        inline=False
                    )
        
        # Get party NPCs
        party_npcs = await cog.db.get_party_npcs(session['id'])
        if party_npcs:
            npc_text = []
            for npc in party_npcs:
                loyalty = npc.get('loyalty', 50)
                loyalty_emoji = "💚" if loyalty >= 75 else "💛" if loyalty >= 50 else "🧡" if loyalty >= 25 else "❤️"
                npc_text.append(f"{loyalty_emoji} **{npc['name']}** ({npc.get('party_role', 'Companion')})")
            embed.add_field(name="🤝 NPC Companions", value="\n".join(npc_text), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GameActionsView(ui.View):
    """View containing game action buttons"""
    
    def __init__(self, cog, options: List[str] = None, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.cog = cog
        
        # Add option buttons if provided (from DM response)
        if options:
            for i, option in enumerate(options[:3], 1):
                self.add_item(PlayerActionButton(
                    label=option[:80],
                    action=f"option_{i}",
                    style=discord.ButtonStyle.primary,
                    emoji="🎯"
                ))
        
        # Add info buttons
        self.add_item(InfoButton(label="Character", info_type="character", emoji="📜"))
        self.add_item(InfoButton(label="Quest", info_type="quest", emoji="📋"))
        self.add_item(InfoButton(label="Location", info_type="location", emoji="🗺️"))
        self.add_item(InfoButton(label="Inventory", info_type="inventory", emoji="🎒"))
        self.add_item(InfoButton(label="Party", info_type="party", emoji="👥"))


class QuickActionsView(ui.View):
    """View for quick action buttons"""
    
    def __init__(self, cog, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.cog = cog
        
        self.add_item(PlayerActionButton(label="Look Around", action="look", emoji="👁️"))
        self.add_item(PlayerActionButton(label="Continue", action="continue", emoji="➡️"))
        self.add_item(InfoButton(label="Character", info_type="character", emoji="📜"))
        self.add_item(InfoButton(label="Quest", info_type="quest", emoji="📋"))
        self.add_item(InfoButton(label="Location", info_type="location", emoji="🗺️"))


class DMChat(commands.Cog):
    """AI Dungeon Master chat handling"""
    
    def __init__(self, bot):
        self.bot = bot
        self.chat_handler = ChatHandler(bot.db, bot.llm, bot.prompts, bot.tool_schemas, bot.tools)
        # Channel conversation histories with session tracking
        # Format: {channel_id: {'session_id': int, 'messages': []}}
        self.histories: Dict[tuple[int, int], Dict] = {}
        # Max history length per channel
        self.max_history = 50
        # Track last activity per channel for proactive prompting
        self.last_activity = {}
        # Message queue for batching player actions
        # Format: {channel_id: {'messages': [], 'task': asyncio.Task}}
        self.message_queue: Dict[int, Dict] = {}
        # Lock for thread-safe message queuing
        self.queue_locks: Dict[int, asyncio.Lock] = {}
    
    @property
    def db(self):
        return self.bot.db
    
    @property
    def llm(self):
        return self.bot.llm
    
    @property
    def tools(self):
        return self.bot.tools
    
    def get_queue_lock(self, channel_id: int) -> asyncio.Lock:
        """Get or create a lock for a channel"""
        if channel_id not in self.queue_locks:
            self.queue_locks[channel_id] = asyncio.Lock()
        return self.queue_locks[channel_id]
    
    async def cog_load(self):
        self.proactive_dm_check.start()

    async def cog_unload(self):
        self.proactive_dm_check.cancel()

    def _history_key(self, guild_id: int, channel_id: int) -> tuple[int, int]:
        return (guild_id, channel_id)

    def get_history(self, guild_id: int, channel_id: int, session_id: int = None) -> list:
        """Get conversation history for a channel, checking session match"""
        key = self._history_key(guild_id, channel_id)
        if key not in self.histories:
            self.histories[key] = {'session_id': session_id, 'messages': []}
        
        # If session changed, clear old history
        if session_id and self.histories[key].get('session_id') != session_id:
            logger.info(f"Session changed for channel {channel_id}, clearing history")
            self.histories[key] = {'session_id': session_id, 'messages': []}
        
        return self.histories[key]['messages']
    
    def add_to_history(self, guild_id: int, channel_id: int, message: dict, session_id: int = None):
        """Add a message to channel history"""
        history = self.get_history(guild_id, channel_id, session_id)
        history.append(message)
        
        # Trim if too long
        if len(history) > self.max_history:
            key = self._history_key(guild_id, channel_id)
            self.histories[key]['messages'] = history[-self.max_history:]
    
    def clear_history(self, guild_id: int, channel_id: int):
        """Clear channel history"""
        self.histories[self._history_key(guild_id, channel_id)] = {'session_id': None, 'messages': []}
    
    def clear_all_guild_histories(self, guild_id: int = None):
        """Clear all histories (or for a specific guild's channels)"""
        if guild_id is None:
            self.histories = {}
            return

        self.histories = {
            key: value for key, value in self.histories.items() if key[0] != guild_id
        }
    
    def start_new_session(self, channel_id: int, session_id: int, guild_id: int = None):
        """Mark a new session as started for a channel - clears old history"""
        if guild_id is None:
            matching_keys = [key for key in self.histories if key[1] == channel_id]
            guild_id = matching_keys[0][0] if matching_keys else 0
        self.histories[self._history_key(guild_id, channel_id)] = {'session_id': session_id, 'messages': []}
        logger.info(f"Started new session {session_id} for channel {channel_id}, cleared history")

    async def resolve_session(self, guild_id: int, user_id: int = None, channel_id: int = None):
        """Resolve the active session for this channel/user context."""
        session_id = await self.get_active_session_id(guild_id, user_id, channel_id)
        return await self.chat_handler.resolve_session(guild_id, session_id=session_id, user_id=user_id)

    def build_full_response(self, response_text: str, mechanics_text: str = "") -> str:
        """Combine mechanics and response text for sending."""
        return self.chat_handler.build_full_response(response_text, mechanics_text)

    def extract_response_options(self, response_text: str) -> List[str]:
        """Extract numbered options from a DM response."""
        return self.chat_handler.extract_response_options(response_text)
    
    async def get_game_context(
        self,
        guild_id: int,
        user_id: int,
        channel_id: int,
        session_id: int = None
    ) -> str:
        """Build context about the current game state
        
        Args:
            guild_id: The guild ID
            user_id: The user ID
            channel_id: The channel ID  
            session_id: Optional - the session ID to use (avoids database lookup if provided)
        """
        return await self.chat_handler.get_game_context(guild_id, user_id, channel_id, session_id)
    
    def get_channel_session_id(self, guild_id: int, channel_id: int) -> Optional[int]:
        """Get the session ID stored for a channel (from when game started in this channel)"""
        key = self._history_key(guild_id, channel_id)
        if key in self.histories:
            return self.histories[key].get('session_id')
        return None
    
    async def get_active_session_id(self, guild_id: int, user_id: int = None, channel_id: int = None) -> Optional[int]:
        """Get the active session ID, prioritizing channel's session over user lookup.
        
        Priority order:
        1. Channel's stored session_id (set when game starts in this channel)
        2. User's active session from database
        3. First active session for the guild (fallback)
        """
        # FIRST: Check if this channel has a session set (most reliable for new games)
        if channel_id:
            channel_session = self.get_channel_session_id(guild_id, channel_id)
            if channel_session:
                logger.debug(f"Using channel's stored session {channel_session} for channel {channel_id}")
                return channel_session
        
        # SECOND: Try to get the session the user is actually in
        if user_id:
            user_session = await self.db.get_user_active_session(guild_id, user_id)
            if user_session:
                logger.debug(f"Using user's active session {user_session['id']} for user {user_id}")
                return user_session['id']
        
        # LAST: Fallback to first active session for the guild
        sessions = await self.db.get_sessions(guild_id, status='active')
        if sessions:
            logger.debug(f"Falling back to first active session {sessions[0]['id']} for guild {guild_id}")
            return sessions[0]['id']
        
        logger.warning(f"No active session found for guild {guild_id}")
        return None
    
    async def process_batched_messages(
        self,
        channel: discord.TextChannel,
        messages: List[Dict]
    ) -> tuple:
        """Process multiple player messages in a single DM response
        
        Returns:
            tuple: (response_text, mechanics_text) - The DM response and formatted game mechanics
        """
        if not messages:
            return "*The Dungeon Master waits for your actions.*", ""

        guild_id = channel.guild.id
        channel_id = channel.id
        first_user_id = messages[0]['user_id']
        session_id = await self.get_active_session_id(guild_id, first_user_id, channel_id)
        self.last_activity[channel_id] = datetime.utcnow()

        history = self.get_history(guild_id, channel_id, session_id)
        result = await self.chat_handler.process_batched_messages(
            guild_id=guild_id,
            channel_id=channel_id,
            messages=messages,
            history=history,
            session_id=session_id,
        )

        self.add_to_history(guild_id, channel_id, result['user_message'], result['session_id'])
        self.add_to_history(guild_id, channel_id, result['assistant_message'], result['session_id'])
        return result['response'], result['mechanics_text']
    
    async def process_dm_input(
        self,
        channel,
        guild,
        author,
        user_message: str
    ) -> tuple:
        """Process a message through the AI DM with tool support
        
        Returns:
            tuple: (response_text, mechanics_text) - The DM response and formatted game mechanics
        """
        channel_id = channel.id
        guild_id = guild.id
        user_id = author.id
        session_id = await self.get_active_session_id(guild_id, user_id, channel_id)
        self.last_activity[channel_id] = datetime.utcnow()

        history = self.get_history(guild_id, channel_id, session_id)
        char = await self.db.get_active_character(user_id, guild_id)
        actor = ChatActor(
            user_id=user_id,
            display_name=author.display_name,
            character_name=char['name'] if char else author.display_name,
            character_id=char['id'] if char else None,
        )
        result = await self.chat_handler.process_single_message(
            guild_id=guild_id,
            channel_id=channel_id,
            actor=actor,
            user_message=user_message,
            history=history,
            session_id=session_id,
        )

        self.add_to_history(guild_id, channel_id, result['user_message'], result['session_id'])
        self.add_to_history(guild_id, channel_id, result['assistant_message'], result['session_id'])
        return result['response'], result['mechanics_text']

    async def process_dm_message(
        self,
        message: discord.Message,
        user_message: str
    ) -> tuple:
        """Compatibility wrapper for Discord message objects."""
        return await self.process_dm_input(message.channel, message.guild, message.author, user_message)
    
    async def queue_player_message(self, message: discord.Message, content: str):
        """Queue a player message for batched processing"""
        channel_id = message.channel.id
        guild_id = message.guild.id
        user_id = message.author.id
        
        # Get character name
        char = await self.db.get_active_character(user_id, guild_id)
        char_name = char['name'] if char else message.author.display_name
        
        lock = self.get_queue_lock(channel_id)
        async with lock:
            # Initialize queue for channel if needed
            if channel_id not in self.message_queue:
                self.message_queue[channel_id] = {
                    'messages': [],
                    'task': None,
                    'channel': message.channel
                }
            
            queue = self.message_queue[channel_id]
            
            # Add message to queue
            queue['messages'].append({
                'user_id': user_id,
                'display_name': message.author.display_name,
                'character_name': char_name,
                'content': content,
                'timestamp': datetime.utcnow()
            })
            
            # Cancel existing task if any (will restart timer)
            if queue.get('task') and not queue['task'].done():
                queue['task'].cancel()
            
            # Start new delayed processing task
            queue['task'] = asyncio.create_task(
                self._delayed_process_queue(channel_id)
            )
    
    async def _delayed_process_queue(self, channel_id: int):
        """Wait for batch delay then process all queued messages"""
        try:
            # Wait for more messages
            await asyncio.sleep(MESSAGE_BATCH_DELAY)
            
            lock = self.get_queue_lock(channel_id)
            async with lock:
                queue = self.message_queue.get(channel_id)
                if not queue or not queue['messages']:
                    return
                
                messages = queue['messages'].copy()
                channel = queue['channel']
                
                # Clear queue
                queue['messages'] = []
                queue['task'] = None
            
            # Process batched messages
            async with channel.typing():
                response, mechanics_text = await self.process_batched_messages(channel, messages)
                
                # Build full response with mechanics
                full_response = self.build_full_response(response, mechanics_text)
                view = GameActionsView(self, options=self.extract_response_options(response))
                await send_chunked(channel, full_response, view=view)
                    
        except asyncio.CancelledError:
            # Task was cancelled, new messages came in - that's fine
            pass
        except Exception as e:
            logger.error(f"Error processing message queue: {e}", exc_info=True)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages in designated DM channels or mentions"""
        # Ignore bots
        if message.author.bot:
            return
        
        # Ignore DMs
        if not message.guild:
            return
        
        # Check if bot was mentioned or if it's a DM channel
        bot_mentioned = self.bot.user in message.mentions
        is_dm_channel = "dungeon-master" in message.channel.name.lower() or "dm-chat" in message.channel.name.lower()
        
        if not (bot_mentioned or is_dm_channel):
            return
        
        # Remove bot mention from message
        content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        content = message.content.replace(f'<@!{self.bot.user.id}>', '').strip()
        
        if not content:
            content = "Hello!"
        
        # Queue for batched processing
        await self.queue_player_message(message, content)
    
    @app_commands.command(name="dm", description="Talk to the Dungeon Master - describe what you want to do!")
    @app_commands.describe(message="What do you want to say or do? Be creative!")
    @app_commands.guild_only()
    async def dm_command(self, interaction: discord.Interaction, message: str):
        """Interact with the AI Dungeon Master"""
        await interaction.response.defer()
        
        # Check if user has a character
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            # Prompt to create character
            embed = discord.Embed(
                title="🎭 Hold, Adventurer!",
                description=(
                    "You haven't created a character yet!\n\n"
                    "Use `/game menu` to create your character and join a game.\n"
                    "The Dungeon Master awaits your arrival!"
                ),
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        response, mechanics_text = await self.process_dm_input(interaction.channel, interaction.guild, interaction.user, message)
        
        # Handle empty/silent responses
        if not response or response.strip() == "" or response == "*The Dungeon Master remains silent.*":
            response = (
                "*The Dungeon Master strokes their beard thoughtfully...*\n\n"
                f"I heard you, **{char['name']}**. You said: \"{message}\"\n\n"
                "What would you like to do? Try being more specific about your action, "
                "or use `/action` for quick options!"
            )
        
        # Build full response with mechanics
        full_response = ""
        if mechanics_text:
            full_response = mechanics_text + "\n"
        full_response += response
        
        # Create view with action buttons
        view = GameActionsView(self, options=self.extract_response_options(response))
        
        # Create embed for response
        embed = discord.Embed(
            description=full_response[:4000],
            color=discord.Color.dark_purple()
        )
        embed.set_author(
            name="🎭 Dungeon Master",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        embed.set_footer(text=f"{char['name']}: \"{message[:50]}{'...' if len(message) > 50 else ''}\"")
        
        await interaction.followup.send(embed=embed, view=view)
    
    @app_commands.command(name="action", description="Quick actions for common RPG activities")
    @app_commands.describe(action="What action do you want to take?")
    @app_commands.choices(action=[
        app_commands.Choice(name="🔍 Look around", value="look"),
        app_commands.Choice(name="👂 Listen carefully", value="listen"),
        app_commands.Choice(name="🚪 Search for secrets", value="search"),
        app_commands.Choice(name="🗣️ Talk to someone nearby", value="talk"),
        app_commands.Choice(name="🎒 Check my inventory", value="inventory"),
        app_commands.Choice(name="❓ What are my options?", value="options"),
        app_commands.Choice(name="⏭️ Continue forward", value="continue"),
    ])
    @app_commands.guild_only()
    async def quick_action(self, interaction: discord.Interaction, action: str):
        """Quick action command for common activities"""
        await interaction.response.defer()
        
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.followup.send(
                "❌ Create a character first with `/game menu`!",
                ephemeral=True
            )
            return
        
        action_prompts = {
            'look': f"{char['name']} looks around carefully, taking in the surroundings. Describe what I see.",
            'listen': f"{char['name']} stops and listens carefully. What do I hear?",
            'search': f"{char['name']} searches the area for hidden objects, traps, or secrets. Roll Investigation/Perception and tell me what I find.",
            'talk': f"{char['name']} approaches the nearest person or creature to talk. Who is nearby and what do they say?",
            'inventory': f"What items does {char['name']} have in their inventory? List them out.",
            'options': f"What are {char['name']}'s options right now? Give me 3-4 things I could do.",
            'continue': f"{char['name']} continues forward with the current objective. What happens next?"
        }
        
        prompt = action_prompts.get(action, "What happens next?")
        
        response, mechanics_text = await self.process_dm_input(interaction.channel, interaction.guild, interaction.user, prompt)
        
        # Build full response with mechanics
        full_response = ""
        if mechanics_text:
            full_response = mechanics_text + "\n"
        full_response += response
        
        action_titles = {
            'look': "👁️ Looking Around",
            'listen': "👂 Listening",
            'search': "🔍 Searching",
            'talk': "🗣️ Conversation",
            'inventory': "🎒 Inventory",
            'options': "❓ Your Options",
            'continue': "⏭️ Moving Forward"
        }
        
        # Create view with action buttons
        view = GameActionsView(self, options=self.extract_response_options(response))
        
        embed = discord.Embed(
            title=action_titles.get(action, "Action"),
            description=full_response[:4000],
            color=discord.Color.dark_purple()
        )
        embed.set_footer(text=f"Playing as {char['name']}")
        
        await interaction.followup.send(embed=embed, view=view)
    
    @app_commands.command(name="narrate", description="Have the DM narrate a scene")
    @app_commands.describe(
        scene="Description of the scene to narrate",
        tone="The tone of the narration"
    )
    @app_commands.choices(tone=[
        app_commands.Choice(name="Epic", value="epic"),
        app_commands.Choice(name="Mysterious", value="mysterious"),
        app_commands.Choice(name="Comedic", value="comedic"),
        app_commands.Choice(name="Tense", value="tense"),
        app_commands.Choice(name="Peaceful", value="peaceful"),
    ])
    @app_commands.guild_only()
    async def narrate(
        self,
        interaction: discord.Interaction,
        scene: str,
        tone: str = "epic"
    ):
        """Have the DM narrate a scene"""
        await interaction.response.defer()
        
        prompt = f"Narrate this scene in a {tone} tone: {scene}"
        
        response, mechanics_text = await self.process_dm_input(interaction.channel, interaction.guild, interaction.user, prompt)
        
        # Build full response with mechanics
        full_response = ""
        if mechanics_text:
            full_response = mechanics_text + "\n"
        full_response += response
        
        embed = discord.Embed(
            title=f"📜 {tone.title()} Narration",
            description=full_response[:4000],
            color=discord.Color.dark_gold()
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="check", description="Make a skill check")
    @app_commands.guild_only()
    @app_commands.describe(
        skill="The skill to check",
        difficulty="The difficulty class (DC)"
    )
    @app_commands.choices(skill=[
        app_commands.Choice(name="Strength", value="strength"),
        app_commands.Choice(name="Dexterity", value="dexterity"),
        app_commands.Choice(name="Constitution", value="constitution"),
        app_commands.Choice(name="Intelligence", value="intelligence"),
        app_commands.Choice(name="Wisdom", value="wisdom"),
        app_commands.Choice(name="Charisma", value="charisma"),
        app_commands.Choice(name="Perception", value="perception"),
        app_commands.Choice(name="Stealth", value="stealth"),
        app_commands.Choice(name="Persuasion", value="persuasion"),
        app_commands.Choice(name="Intimidation", value="intimidation"),
        app_commands.Choice(name="Investigation", value="investigation"),
        app_commands.Choice(name="Athletics", value="athletics"),
        app_commands.Choice(name="Acrobatics", value="acrobatics"),
    ])
    async def skill_check(
        self,
        interaction: discord.Interaction,
        skill: str,
        difficulty: Optional[int] = None
    ):
        """Make a skill check with DM narration"""
        await interaction.response.defer()
        
        dc_text = f" against DC {difficulty}" if difficulty else ""
        prompt = f"I want to make a {skill} check{dc_text}. Roll the dice and narrate the result."
        
        response, mechanics_text = await self.process_dm_input(interaction.channel, interaction.guild, interaction.user, prompt)
        
        # Build full response with mechanics
        full_response = ""
        if mechanics_text:
            full_response = mechanics_text + "\n"
        full_response += response
        
        # Create view with action buttons
        view = GameActionsView(self, options=self.extract_response_options(response))
        
        embed = discord.Embed(
            title=f"🎲 {skill.title()} Check",
            description=full_response[:4000],
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=view)
    
    @app_commands.command(name="dm_clear", description="Clear the DM conversation history")
    @app_commands.guild_only()
    async def clear_dm_history(self, interaction: discord.Interaction):
        """Clear conversation history"""
        self.clear_history(interaction.guild.id, interaction.channel.id)
        
        await interaction.response.send_message(
            "🧹 The Dungeon Master's memory has been cleared for this channel.",
            ephemeral=True
        )
    
    @app_commands.command(name="scene", description="Set the scene for the adventure")
    @app_commands.describe(description="Description of the current scene/location")
    @app_commands.guild_only()
    async def set_scene(self, interaction: discord.Interaction, description: str):
        """Set a scene for the DM to build upon"""
        await interaction.response.defer()
        
        prompt = f"Set the following scene for our adventure and describe what the players see, hear, and feel: {description}"
        
        response, mechanics_text = await self.process_dm_input(interaction.channel, interaction.guild, interaction.user, prompt)
        
        # Build full response with mechanics
        full_response = ""
        if mechanics_text:
            full_response = mechanics_text + "\n"
        full_response += response
        
        # Create view with action buttons
        view = GameActionsView(self, options=self.extract_response_options(response))
        
        embed = discord.Embed(
            title="🏰 Scene Set",
            description=full_response[:4000],
            color=discord.Color.dark_green()
        )
        
        await interaction.followup.send(embed=embed, view=view)
    
    @app_commands.command(name="reset", description="Reset the DM's memory for this channel (clears conversation history)")
    @app_commands.guild_only()
    async def reset_history(self, interaction: discord.Interaction):
        """Clear the conversation history for this channel"""
        channel_id = interaction.channel.id
        
        self.clear_history(interaction.guild.id, channel_id)
        
        # Also clear message queue if any
        if channel_id in self.message_queue:
            if self.message_queue[channel_id].get('task'):
                self.message_queue[channel_id]['task'].cancel()
            del self.message_queue[channel_id]
        
        embed = discord.Embed(
            title="🔄 Memory Reset",
            description=(
                "The Dungeon Master's memory for this channel has been cleared!\n\n"
                "**What this means:**\n"
                "• Previous conversation context is forgotten\n"
                "• Game state and character data is preserved\n"
                "• The DM will start fresh in this channel\n\n"
                "Use `/game begin [id]` to restart your adventure with a fresh intro!"
            ),
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)

    async def _generate_proactive_nudge(self, channel: discord.TextChannel) -> Optional[str]:
        """Generate a proactive DM response after channel inactivity."""
        if not self.llm:
            return None

        session = await self.resolve_session(channel.guild.id, channel_id=channel.id)
        session_id = session['id'] if session else None
        history = self.get_history(channel.guild.id, channel.id, session_id)
        game_context = await self.get_game_context(channel.guild.id, 0, channel.id, session_id)

        messages = [
            {
                'role': 'system',
                'content': f"{self.bot.prompts.get_dm_system_prompt()}\n\n{PROACTIVE_DM_GUIDELINES}\n\nCURRENT GAME STATE:\n{game_context}",
            },
            *history,
            {
                'role': 'user',
                'content': 'The party has been quiet for a while. Give a proactive, in-world nudge and end with a clear prompt for action.',
            },
        ]

        response = await self.llm.chat_with_tools(messages=messages, tools=self.bot.tool_schemas.get_all_schemas())
        return response.get('content') if response else None

    @tasks.loop(minutes=1)
    async def proactive_dm_check(self):
        """Prompt inactive channels with a gentle DM nudge."""
        now = datetime.utcnow()
        for channel_id, last_time in list(self.last_activity.items()):
            elapsed = (now - last_time).total_seconds()
            if elapsed <= 1800 or elapsed >= 7200:
                continue

            queue = self.message_queue.get(channel_id)
            if queue and queue.get('messages'):
                continue

            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            try:
                response = await self._generate_proactive_nudge(channel)
                if not response:
                    continue
                view = GameActionsView(self, options=self.extract_response_options(response))
                await send_chunked(channel, response, view=view)
                self.last_activity[channel_id] = now
            except Exception as exc:
                logger.warning(f"Failed proactive DM nudge for channel {channel_id}: {exc}")

    @proactive_dm_check.before_loop
    async def before_proactive_dm_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DMChat(bot))
