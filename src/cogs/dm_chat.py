"""
RPG DM Bot - DM Chat Cog
Handles AI Dungeon Master interactions with tool execution
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord import ui
import logging
import json
import asyncio
from typing import Optional, Dict, List
from datetime import datetime

from src.mechanics_tracker import new_tracker, get_tracker

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
            'option_1': f"{char['name']} chooses option 1.",
            'option_2': f"{char['name']} chooses option 2.",
            'option_3': f"{char['name']} chooses option 3.",
            'look': f"{char['name']} looks around carefully.",
            'continue': f"{char['name']} continues forward.",
        }
        
        prompt = action_prompts.get(self.action, f"{char['name']} does: {self.action}")
        
        # Process through DM
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        response = await cog.process_dm_message(FakeMessage(interaction), prompt)
        
        # Get mechanics display
        tracker = get_tracker()
        mechanics_text = tracker.format_all() if tracker.has_mechanics() else ""
        
        # Build response
        full_response = ""
        if mechanics_text:
            full_response = mechanics_text + "\n"
        full_response += response
        
        # Create new view with buttons
        view = GameActionsView(cog)
        
        # Send response
        if len(full_response) > 2000:
            chunks = [full_response[i:i+2000] for i in range(0, len(full_response), 2000)]
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:
                    await interaction.followup.send(chunk, view=view)
                else:
                    await interaction.followup.send(chunk)
        else:
            await interaction.followup.send(full_response, view=view)


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
        session = await cog.db.get_user_active_session(interaction.guild.id, interaction.user.id)
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
        session = await cog.db.get_user_active_session(interaction.guild.id, interaction.user.id)
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
        session = await cog.db.get_user_active_session(interaction.guild.id, interaction.user.id)
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
                    label=f"Option {i}",
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
        # Channel conversation histories with session tracking
        # Format: {channel_id: {'session_id': int, 'messages': []}}
        self.histories: Dict[int, Dict] = {}
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
    
    def get_history(self, channel_id: int, session_id: int = None) -> list:
        """Get conversation history for a channel, checking session match"""
        if channel_id not in self.histories:
            self.histories[channel_id] = {'session_id': session_id, 'messages': []}
        
        # If session changed, clear old history
        if session_id and self.histories[channel_id].get('session_id') != session_id:
            logger.info(f"Session changed for channel {channel_id}, clearing history")
            self.histories[channel_id] = {'session_id': session_id, 'messages': []}
        
        return self.histories[channel_id]['messages']
    
    def add_to_history(self, channel_id: int, message: dict, session_id: int = None):
        """Add a message to channel history"""
        history = self.get_history(channel_id, session_id)
        history.append(message)
        
        # Trim if too long
        if len(history) > self.max_history:
            self.histories[channel_id]['messages'] = history[-self.max_history:]
    
    def clear_history(self, channel_id: int):
        """Clear channel history"""
        self.histories[channel_id] = {'session_id': None, 'messages': []}
    
    def clear_all_guild_histories(self, guild_id: int = None):
        """Clear all histories (or for a specific guild's channels)"""
        if guild_id is None:
            self.histories = {}
        # Note: We can't easily filter by guild without channel info
        # This is called when starting a new game to reset context
    
    def start_new_session(self, channel_id: int, session_id: int):
        """Mark a new session as started for a channel - clears old history"""
        self.histories[channel_id] = {'session_id': session_id, 'messages': []}
        logger.info(f"Started new session {session_id} for channel {channel_id}, cleared history")
    
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
        context_parts = []
        
        # Get user's character with full details
        char = await self.db.get_active_character(user_id, guild_id)
        if char:
            char_class = char.get('char_class') or char.get('class', 'Unknown')
            context_parts.append(f"""
PLAYER CHARACTER:
- Name: {char['name']}
- Class: {char_class} | Race: {char['race']}
- Level: {char['level']} | XP: {char.get('xp', char.get('experience', 0))}
- HP: {char['hp']}/{char['max_hp']}
- Stats: STR {char['strength']}, DEX {char['dexterity']}, CON {char['constitution']}, INT {char['intelligence']}, WIS {char['wisdom']}, CHA {char['charisma']}
- Gold: {char['gold']}""")
            
            # Include backstory if available
            if char.get('backstory'):
                context_parts.append(f"- Backstory: {char['backstory']}")
            
            # Get character's current location if set
            if char.get('current_location_id'):
                char_location = await self.db.get_location(char['current_location_id'])
                if char_location:
                    context_parts.append(f"- Current Location: {char_location['name']}")
        
        # Get active session - use provided session_id or look it up
        session = None
        if session_id:
            session = await self.db.get_session(session_id)
            if session:
                logger.debug(f"get_game_context: Using provided session_id {session_id} ({session['name']})")
        if not session:
            # Fallback: get session from channel or user
            session = await self.db.get_user_active_session(guild_id, user_id)
            if session:
                logger.debug(f"get_game_context: Fell back to user session {session['id']} ({session['name']})")
        if not session:
            # Last fallback: first active session for the guild
            sessions = await self.db.get_sessions(guild_id, status='active')
            session = sessions[0] if sessions else None
            if session:
                logger.debug(f"get_game_context: Fell back to first guild session {session['id']} ({session['name']})")
        
        if session:
            context_parts.append(f"""
ACTIVE SESSION: {session['name']}
Game Description: {session.get('description', 'An adventure awaits!')}""")
            
            # Get all party members with backstories
            players = await self.db.get_session_players(session['id'])
            if players:
                context_parts.append("\nPARTY MEMBERS:")
                for p in players:
                    # Skip players without a character assigned
                    if not p.get('character_id'):
                        continue
                    party_char = await self.db.get_character(p['character_id'])
                    if party_char:
                        pc_class = party_char.get('char_class') or party_char.get('class', 'Unknown')
                        context_parts.append(f"- {party_char['name']}: Level {party_char['level']} {party_char['race']} {pc_class}")
                        context_parts.append(f"  HP: {party_char['hp']}/{party_char['max_hp']}")
                        if party_char.get('backstory'):
                            context_parts.append(f"  Backstory: {party_char['backstory'][:200]}...")
            
            # Get game state for persistent context
            game_state = await self.db.get_game_state(session['id'])
            current_location = None
            if game_state:
                if game_state.get('current_scene'):
                    context_parts.append(f"\nCURRENT SCENE: {game_state['current_scene']}")
                if game_state.get('current_location'):
                    context_parts.append(f"CURRENT LOCATION (NAME): {game_state['current_location']}")
                if game_state.get('current_location_id'):
                    current_location = await self.db.get_location(game_state['current_location_id'])
                if game_state.get('dm_notes'):
                    context_parts.append(f"DM NOTES: {game_state['dm_notes']}")
            
            # Enhanced location context
            if current_location:
                loc_details = [f"\nLOCATION DETAILS ({current_location['name']}):"]
                loc_details.append(f"- Type: {current_location.get('location_type', 'generic')}")
                loc_details.append(f"- Description: {current_location.get('description', 'Unknown')}")
                if current_location.get('current_weather'):
                    loc_details.append(f"- Weather: {current_location['current_weather']}")
                if current_location.get('danger_level', 0) > 0:
                    danger = current_location['danger_level']
                    danger_text = "Low" if danger < 3 else "Moderate" if danger < 5 else "High" if danger < 8 else "Deadly"
                    loc_details.append(f"- Danger Level: {danger_text}")
                if current_location.get('points_of_interest'):
                    poi = current_location['points_of_interest']
                    if isinstance(poi, list):
                        loc_details.append(f"- Points of Interest: {', '.join(poi)}")
                context_parts.extend(loc_details)
                
                # Get NPCs at this location
                npcs_at_location = await self.db.get_npcs_at_location(current_location['id'])
                if npcs_at_location:
                    context_parts.append("\nNPCS AT THIS LOCATION:")
                    for npc in npcs_at_location[:5]:  # Limit to 5 for context size
                        merchant = " (Merchant)" if npc.get('is_merchant') else ""
                        context_parts.append(f"- {npc['name']}{merchant} ({npc.get('npc_type', 'neutral')})")
                        if npc.get('personality'):
                            context_parts.append(f"  Personality: {npc['personality'][:100]}...")
                
                # Get nearby locations
                nearby = await self.db.get_nearby_locations(current_location['id'])
                if nearby:
                    context_parts.append("\nNEARBY LOCATIONS (EXITS):")
                    for loc in nearby[:5]:
                        direction = f" ({loc.get('direction', 'path')})" if loc.get('direction') else ""
                        context_parts.append(f"- {loc.get('to_name', loc.get('name', 'Unknown'))}{direction}")
                
                # Get story items at this location
                story_items = await self.db.get_story_items_at_location(current_location['id'])
                if story_items:
                    context_parts.append("\nSTORY ITEMS HERE:")
                    for item in story_items[:5]:
                        discovered = "(Discovered)" if item.get('is_discovered') else "(Hidden)"
                        context_parts.append(f"- {item['name']} {discovered}: {item.get('description', '')[:60]}...")
            
            # Get active story events
            active_events = await self.db.get_active_events(session['id'])
            if active_events:
                context_parts.append("\nACTIVE STORY EVENTS:")
                for event in active_events[:3]:  # Limit for context size
                    context_parts.append(f"- {event['name']} ({event.get('event_type', 'unknown')})")
                    if event.get('description'):
                        context_parts.append(f"  {event['description'][:100]}...")
            
            # Get session quest
            if session.get('current_quest_id'):
                quest = await self.db.get_quest(session['current_quest_id'])
                if quest:
                    stages = await self.db.get_quest_stages(quest['id'])
                    current_stage = stages[quest['current_stage']] if quest['current_stage'] < len(stages) else None
                    
                    context_parts.append(f"""
CURRENT QUEST: {quest['title']}
Description: {quest['description']}
Difficulty: {quest['difficulty']}
Stage: {quest['current_stage'] + 1}/{len(stages)}""")
                    if current_stage:
                        context_parts.append(f"""
CURRENT STAGE: {current_stage['title']}
{current_stage['description']}""")
        
        # Get active combat
        combat = await self.db.get_active_combat(guild_id, channel_id)
        if combat:
            participants = await self.db.get_combat_participants(combat['id'])
            context_parts.append(f"\nACTIVE COMBAT:")
            context_parts.append(f"Turn: {combat['current_turn']}")
            context_parts.append("Combatants:")
            for p in participants:
                # Skip participants without a character assigned
                if not p.get('character_id'):
                    continue
                char_info = await self.db.get_character(p['character_id'])
                if char_info:
                    context_parts.append(f"- {char_info['name']}: {p['current_hp']} HP, Initiative {p['initiative']}")
        
        return "\n".join(context_parts) if context_parts else "No active game context."
    
    def get_channel_session_id(self, channel_id: int) -> Optional[int]:
        """Get the session ID stored for a channel (from when game started in this channel)"""
        if channel_id in self.histories:
            return self.histories[channel_id].get('session_id')
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
            channel_session = self.get_channel_session_id(channel_id)
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
        
        # Initialize new mechanics tracker for this message
        tracker = new_tracker()
        
        guild_id = channel.guild.id
        channel_id = channel.id
        
        # Get game context using first player's ID (for their character)
        # but context includes all party members
        first_user_id = messages[0]['user_id']
        
        # Get session ID for history tracking - prioritize channel's session over user lookup
        session_id = await self.get_active_session_id(guild_id, first_user_id, channel_id)
        
        # Track activity
        self.last_activity[channel_id] = datetime.utcnow()
        
        game_context = await self.get_game_context(guild_id, first_user_id, channel_id, session_id)
        
        # Build multi-player instruction
        player_actions = "\n".join([
            f"**{msg['display_name']}** ({msg['character_name']}): {msg['content']}"
            for msg in messages
        ])
        
        multi_player_instructions = """
**MULTI-PLAYER HANDLING:**
Multiple players may act simultaneously. Handle each player's action in sequence:
1. Acknowledge each player's declared action by name
2. Roll any needed checks FOR THE SPECIFIC PLAYER taking that action
3. Describe the results for each player
4. If players are doing different things, describe each separately but in the same scene
5. Keep all players in the same location unless they explicitly split up
6. End with a prompt that addresses the whole party

IMPORTANT: Each player's action is prefixed with their name. Make sure you address each player's action!
"""
        
        # Build system prompt with context and proactive guidelines
        system_prompt = f"""{self.bot.prompts.get_dm_system_prompt()}

{PROACTIVE_DM_GUIDELINES}

{multi_player_instructions}

CURRENT GAME STATE:
{game_context}

TOOLS AVAILABLE:
You have access to tools for managing the game. Use them when players want to:
- Create/modify characters
- Manage inventory and items  
- Roll dice for checks and combat
- Control NPCs and dialogue
- Manage quests and progression
- Run combat encounters

Always use dice rolls for skill checks and combat. Make the game interactive and engaging.

CRITICAL: 
- Always end your response with a prompt for player action. Keep the game moving!
- Address ALL player actions in your response, not just one!
- Use get_character_info if you need to know who a player is playing
"""
        
        # Get conversation history (with session checking)
        history = self.get_history(channel_id, session_id)
        
        # Add batched player messages as a single user turn
        batched_content = f"[PLAYER ACTIONS THIS TURN]\n{player_actions}"
        user_msg = {"role": "user", "content": batched_content}
        self.add_to_history(channel_id, user_msg, session_id)
        
        # Build messages for LLM
        messages_for_llm = [
            {"role": "system", "content": system_prompt},
            *history
        ]
        
        # Get tool schemas
        tool_schemas = self.bot.tool_schemas.get_all_schemas()
        
        # Process with tool loop
        response_text = ""
        
        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                response = await self.llm.chat_with_tools(
                    messages=messages_for_llm,
                    tools=tool_schemas
                )
                
                # Check for tool calls
                tool_calls = response.get('tool_calls', [])
                content = response.get('content', '')
                
                if not tool_calls:
                    # No more tools, we have final response
                    response_text = content
                    break
                
                # Execute tools
                for tool_call in tool_calls:
                    tool_name = tool_call['function']['name']
                    try:
                        tool_args = json.loads(tool_call['function']['arguments'])
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Build context for tool execution - include session_id for proper isolation
                    context = {
                        'guild_id': guild_id,
                        'user_id': first_user_id,
                        'channel_id': channel_id,
                        'session_id': session_id  # Critical for session isolation
                    }
                    
                    # Execute the tool
                    tool_result = await self.tools.execute_tool(
                        tool_name,
                        tool_args,
                        context
                    )
                    
                    # Add tool call and result to messages
                    messages_for_llm.append({
                        "role": "assistant",
                        "content": content,
                        "tool_calls": [tool_call]
                    })
                    messages_for_llm.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                    })
                
            except Exception as e:
                logger.error(f"Error in DM chat: {e}", exc_info=True)
                response_text = f"*The Dungeon Master pauses, gathering their thoughts...* (Error: {str(e)[:100]})"
                break
        
        # Add response to history
        if response_text:
            self.add_to_history(channel_id, {"role": "assistant", "content": response_text}, session_id)
        
        # Get formatted mechanics
        mechanics_text = tracker.format_all() if tracker.has_mechanics() else ""
        
        return response_text or "*The Dungeon Master remains silent.*", mechanics_text
    
    async def process_dm_message(
        self,
        message: discord.Message,
        user_message: str
    ) -> tuple:
        """Process a message through the AI DM with tool support
        
        Returns:
            tuple: (response_text, mechanics_text) - The DM response and formatted game mechanics
        """
        channel_id = message.channel.id
        guild_id = message.guild.id
        user_id = message.author.id
        
        # Initialize new mechanics tracker for this message
        tracker = new_tracker()
        
        # Get session ID for history tracking - prioritize channel's session over user lookup
        session_id = await self.get_active_session_id(guild_id, user_id, channel_id)
        
        # Track activity
        self.last_activity[channel_id] = datetime.utcnow()
        
        # Get game context
        game_context = await self.get_game_context(guild_id, user_id, channel_id, session_id)
        
        # Build system prompt with context and proactive guidelines
        system_prompt = f"""{self.bot.prompts.get_dm_system_prompt()}

{PROACTIVE_DM_GUIDELINES}

CURRENT GAME STATE:
{game_context}

TOOLS AVAILABLE:
You have access to tools for managing the game. Use them when players want to:
- Create/modify characters
- Manage inventory and items  
- Roll dice for checks and combat
- Control NPCs and dialogue
- Manage quests and progression
- Run combat encounters

Always use dice rolls for skill checks and combat. Make the game interactive and engaging.

CRITICAL: Always end your response with a prompt for player action. Keep the game moving!
"""
        
        # Get conversation history (with session tracking)
        history = self.get_history(channel_id, session_id)
        
        # Get character name for this player
        char = await self.db.get_active_character(user_id, guild_id)
        char_name = char['name'] if char else message.author.display_name
        
        # Add user message to history with character name
        user_msg = {"role": "user", "content": f"[{message.author.display_name}] ({char_name}): {user_message}"}
        self.add_to_history(channel_id, user_msg, session_id)
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": system_prompt},
            *history
        ]
        
        # Get tool schemas
        tool_schemas = self.bot.tool_schemas.get_all_schemas()
        
        # Process with tool loop
        response_text = ""
        
        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                response = await self.llm.chat_with_tools(
                    messages=messages,
                    tools=tool_schemas
                )
                
                # Check for tool calls
                tool_calls = response.get('tool_calls', [])
                content = response.get('content', '')
                
                if not tool_calls:
                    # No more tools, we have final response
                    response_text = content
                    break
                
                # Execute tools
                for tool_call in tool_calls:
                    tool_name = tool_call['function']['name']
                    try:
                        tool_args = json.loads(tool_call['function']['arguments'])
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Build context for tool execution - include session_id for proper isolation
                    context = {
                        'guild_id': guild_id,
                        'user_id': user_id,
                        'channel_id': channel_id,
                        'session_id': session_id  # Critical for session isolation
                    }
                    
                    # Execute the tool
                    tool_result = await self.tools.execute_tool(
                        tool_name,
                        tool_args,
                        context
                    )
                    
                    # Add tool call and result to messages
                    messages.append({
                        "role": "assistant",
                        "content": content,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                    })
                
            except Exception as e:
                logger.error(f"Error in DM chat: {e}", exc_info=True)
                response_text = f"*The Dungeon Master pauses, gathering their thoughts...* (Error: {str(e)[:100]})"
                break
        
        # Add response to history
        if response_text:
            self.add_to_history(channel_id, {"role": "assistant", "content": response_text}, session_id)
        
        # Get formatted mechanics
        mechanics_text = tracker.format_all() if tracker.has_mechanics() else ""
        
        return response_text or "*The Dungeon Master remains silent.*", mechanics_text
    
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
                full_response = ""
                if mechanics_text:
                    full_response = mechanics_text + "\n"
                full_response += response
                
                # Create view with action buttons
                view = GameActionsView(self)
                
                # Split response if too long
                if len(full_response) > 2000:
                    chunks = [full_response[i:i+2000] for i in range(0, len(full_response), 2000)]
                    for i, chunk in enumerate(chunks):
                        if i == len(chunks) - 1:
                            # Add buttons to last chunk
                            await channel.send(chunk, view=view)
                        else:
                            await channel.send(chunk)
                else:
                    await channel.send(full_response, view=view)
                    
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
        
        # Create a fake message object for processing
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = message
        
        fake_msg = FakeMessage(interaction)
        response, mechanics_text = await self.process_dm_message(fake_msg, message)
        
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
        view = GameActionsView(self)
        
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
        
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        fake_msg = FakeMessage(interaction)
        response, mechanics_text = await self.process_dm_message(fake_msg, prompt)
        
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
        view = GameActionsView(self)
        
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
        
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        fake_msg = FakeMessage(interaction)
        response, mechanics_text = await self.process_dm_message(fake_msg, prompt)
        
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
        
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        fake_msg = FakeMessage(interaction)
        response, mechanics_text = await self.process_dm_message(fake_msg, prompt)
        
        # Build full response with mechanics
        full_response = ""
        if mechanics_text:
            full_response = mechanics_text + "\n"
        full_response += response
        
        # Create view with action buttons
        view = GameActionsView(self)
        
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
        self.clear_history(interaction.channel.id)
        
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
        
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        fake_msg = FakeMessage(interaction)
        response, mechanics_text = await self.process_dm_message(fake_msg, prompt)
        
        # Build full response with mechanics
        full_response = ""
        if mechanics_text:
            full_response = mechanics_text + "\n"
        full_response += response
        
        # Create view with action buttons
        view = GameActionsView(self)
        
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
        
        self.clear_history(channel_id)
        
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


async def setup(bot):
    await bot.add_cog(DMChat(bot))
