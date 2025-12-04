"""
RPG DM Bot - Game Master Cog
Handles game flow, session management, character interviews, and DM private messaging.
The session creator gets DM'd for meta/admin things.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import asyncio

logger = logging.getLogger('rpg.game_master')


# Required character fields for a complete character
REQUIRED_CHARACTER_FIELDS = {
    'name': 'What is your character\'s name?',
    'race': 'What race is your character? (Human, Elf, Dwarf, Halfling, Orc, Tiefling, Dragonborn, Gnome)',
    'char_class': 'What class is your character? (Warrior, Mage, Rogue, Cleric, Ranger, Bard, Paladin, Warlock)',
    'backstory': 'Tell me a bit about your character\'s backstory. Where did they come from? What drives them?',
}

# Fields that improve the game experience
OPTIONAL_CHARACTER_FIELDS = {
    'personality': 'How would you describe your character\'s personality in a few words?',
    'motivation': 'What is your character\'s primary motivation or goal?',
    'fear': 'What does your character fear most?',
    'bond': 'Who or what is most important to your character?',
}


class CharacterInterviewView(discord.ui.View):
    """View for character interview with quick response options"""
    
    def __init__(self, game_master_cog, user_id: int, guild_id: int, field: str):
        super().__init__(timeout=600)
        self.game_master = game_master_cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.field = field
        
        # Add quick options for race/class selection
        if field == 'race':
            self.add_race_buttons()
        elif field == 'char_class':
            self.add_class_buttons()
    
    def add_race_buttons(self):
        races = ['Human', 'Elf', 'Dwarf', 'Halfling', 'Orc', 'Tiefling', 'Dragonborn', 'Gnome']
        for i, race in enumerate(races[:4]):
            btn = discord.ui.Button(label=race, style=discord.ButtonStyle.primary, row=0)
            btn.callback = self.make_race_callback(race)
            self.add_item(btn)
        for i, race in enumerate(races[4:]):
            btn = discord.ui.Button(label=race, style=discord.ButtonStyle.primary, row=1)
            btn.callback = self.make_race_callback(race)
            self.add_item(btn)
    
    def add_class_buttons(self):
        classes = ['Warrior', 'Mage', 'Rogue', 'Cleric', 'Ranger', 'Bard', 'Paladin', 'Warlock']
        for i, char_class in enumerate(classes[:4]):
            btn = discord.ui.Button(label=char_class, style=discord.ButtonStyle.success, row=0)
            btn.callback = self.make_class_callback(char_class)
            self.add_item(btn)
        for i, char_class in enumerate(classes[4:]):
            btn = discord.ui.Button(label=char_class, style=discord.ButtonStyle.success, row=1)
            btn.callback = self.make_class_callback(char_class)
            self.add_item(btn)
    
    def make_race_callback(self, race: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            await self.game_master.process_interview_response(
                interaction.user.id, 
                self.guild_id, 
                'race', 
                race,
                interaction.channel
            )
        return callback
    
    def make_class_callback(self, char_class: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            await self.game_master.process_interview_response(
                interaction.user.id, 
                self.guild_id, 
                'char_class', 
                char_class,
                interaction.channel
            )
        return callback


class QuickStartView(discord.ui.View):
    """View for quick game start options"""
    
    def __init__(self, game_master_cog):
        super().__init__(timeout=300)
        self.game_master = game_master_cog
    
    @discord.ui.button(label="🎮 Start New Game", style=discord.ButtonStyle.success, row=0)
    async def start_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start a new game session"""
        modal = QuickStartModal(self.game_master)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="👤 Create Character", style=discord.ButtonStyle.primary, row=0)
    async def create_character(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start character creation"""
        # Start the interview process
        await interaction.response.defer(ephemeral=True)
        await self.game_master.start_character_interview(interaction.user, interaction.guild)
        await interaction.followup.send(
            "✨ Check your DMs! The Dungeon Master will help you create your character.",
            ephemeral=True
        )
    
    @discord.ui.button(label="📋 Join Existing Game", style=discord.ButtonStyle.secondary, row=0)
    async def join_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show available games to join"""
        sessions = await self.game_master.bot.db.get_sessions(interaction.guild.id, status='active')
        
        if not sessions:
            sessions = await self.game_master.bot.db.get_sessions(interaction.guild.id, status='inactive')
        
        if not sessions:
            await interaction.response.send_message(
                "❌ No games available to join. Start a new one with the button above!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎲 Available Games",
            description="Click a button to join a game:",
            color=discord.Color.blue()
        )
        
        view = GameListView(self.game_master, sessions[:5])  # Show up to 5
        
        for session in sessions[:5]:
            dm = interaction.guild.get_member(session['dm_user_id'])
            dm_name = dm.display_name if dm else "Unknown"
            players = await self.game_master.bot.db.get_session_players(session['id'])
            
            status_emoji = "🟢" if session['status'] == 'active' else "🟡"
            embed.add_field(
                name=f"{status_emoji} {session['name']}",
                value=f"DM: {dm_name}\nPlayers: {len(players)}/{session['max_players']}\n`/game join {session['id']}`",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="❓ How to Play", style=discord.ButtonStyle.secondary, row=1)
    async def how_to_play(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show how to play guide"""
        embed = discord.Embed(
            title="📖 How to Play",
            description="Welcome to the AI Dungeon Master RPG!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="1️⃣ Create a Character",
            value="Use `/character create` or click the button above. The DM will interview you to build your character!",
            inline=False
        )
        
        embed.add_field(
            name="2️⃣ Join or Start a Game",
            value="Start a new game with `/game start` or join an existing one with `/game join`",
            inline=False
        )
        
        embed.add_field(
            name="3️⃣ Play the Game",
            value="@mention the bot or use `/dm` to talk to the Dungeon Master. Describe what you want to do!",
            inline=False
        )
        
        embed.add_field(
            name="4️⃣ Rolling Dice",
            value="Use `/roll dice 1d20` or let the DM roll for you when you take actions",
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value="• Be creative with your actions!\n• The DM responds to roleplay\n• Explore, fight, talk to NPCs\n• Your choices matter!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class QuickStartModal(discord.ui.Modal, title="Start New Game"):
    """Modal for quickly starting a new game"""
    
    game_name = discord.ui.TextInput(
        label="Game Name",
        placeholder="The Dragon's Lair",
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Brief Description (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="A mysterious dungeon has appeared near the village...",
        max_length=300,
        required=False
    )
    
    def __init__(self, game_master_cog):
        super().__init__()
        self.game_master = game_master_cog
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Create the session
        session_id = await self.game_master.bot.db.create_session(
            guild_id=interaction.guild.id,
            name=str(self.game_name),
            description=str(self.description) if self.description.value else "A new adventure awaits!",
            dm_user_id=interaction.user.id,
            max_players=6
        )
        
        # Get or create character for the game creator
        char = await self.game_master.bot.db.get_active_character(
            interaction.user.id, 
            interaction.guild.id
        )
        
        # Send DM to session creator about game management
        try:
            dm_channel = await interaction.user.create_dm()
            
            admin_embed = discord.Embed(
                title="🎭 You're Now the Dungeon Master!",
                description=f"You've created **{self.game_name}**. Here are your admin controls:",
                color=discord.Color.purple()
            )
            
            admin_embed.add_field(
                name="🎮 Game Commands",
                value=(
                    f"`/game begin {session_id}` - Start the adventure\n"
                    f"`/game pause {session_id}` - Pause the game\n"
                    f"`/game end {session_id}` - End the session\n"
                    f"`/game status {session_id}` - Check game status"
                ),
                inline=False
            )
            
            admin_embed.add_field(
                name="📢 Announcements",
                value="I'll DM you privately for meta things like:\n• Player issues\n• Story planning suggestions\n• Game management alerts",
                inline=False
            )
            
            admin_embed.add_field(
                name="💡 Tips",
                value="• Let the AI DM run the story\n• You can guide it with `/dm` commands\n• Use `/narrate` to set scenes\n• The AI remembers the story!",
                inline=False
            )
            
            await dm_channel.send(embed=admin_embed)
            
        except discord.Forbidden:
            logger.warning(f"Could not DM user {interaction.user.id}")
        
        # Handle character situation
        if not char:
            # No character - start interview
            embed = discord.Embed(
                title=f"🎲 Game Created: {self.game_name}",
                description=(
                    "Your game is ready! But you need a character to play.\n\n"
                    "**Check your DMs** - The Dungeon Master will help you create one!"
                ),
                color=discord.Color.green()
            )
            embed.add_field(name="Session ID", value=str(session_id), inline=True)
            embed.add_field(name="Players", value="Waiting for characters...", inline=True)
            
            await interaction.followup.send(embed=embed)
            await self.game_master.start_character_interview(interaction.user, interaction.guild)
            
        else:
            # Has character - add to session and offer to start
            await self.game_master.bot.db.add_session_player(session_id, char['id'])
            
            embed = discord.Embed(
                title=f"🎲 Game Created: {self.game_name}",
                description=f"**{char['name']}** is ready to adventure!",
                color=discord.Color.green()
            )
            embed.add_field(name="Session ID", value=str(session_id), inline=True)
            embed.add_field(name="Your Character", value=f"{char['name']} the {char['race']} {char['class']}", inline=True)
            embed.add_field(
                name="Next Steps",
                value=f"• Share the session ID for others to join\n• Use `/game begin {session_id}` when ready to start!",
                inline=False
            )
            
            view = BeginGameView(self.game_master, session_id)
            await interaction.followup.send(embed=embed, view=view)


class BeginGameView(discord.ui.View):
    """View to begin the game"""
    
    def __init__(self, game_master_cog, session_id: int):
        super().__init__(timeout=600)
        self.game_master = game_master_cog
        self.session_id = session_id
    
    @discord.ui.button(label="⚔️ Begin Adventure!", style=discord.ButtonStyle.success)
    async def begin_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Begin the game"""
        await self.game_master.begin_game(interaction, self.session_id)
        self.stop()
    
    @discord.ui.button(label="⏳ Wait for More Players", style=discord.ButtonStyle.secondary)
    async def wait_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Just acknowledge waiting"""
        await interaction.response.send_message(
            f"👍 Take your time! Use `/game begin {self.session_id}` when everyone's ready.",
            ephemeral=True
        )


class GameListView(discord.ui.View):
    """View for listing and joining games"""
    
    def __init__(self, game_master_cog, sessions: List[Dict]):
        super().__init__(timeout=300)
        self.game_master = game_master_cog
        
        # Add join buttons for each session
        for i, session in enumerate(sessions[:5]):
            btn = discord.ui.Button(
                label=f"Join: {session['name'][:20]}",
                style=discord.ButtonStyle.success,
                custom_id=f"join_{session['id']}",
                row=i
            )
            btn.callback = self.make_join_callback(session['id'], session['name'])
            self.add_item(btn)
    
    def make_join_callback(self, session_id: int, session_name: str):
        async def callback(interaction: discord.Interaction):
            char = await self.game_master.bot.db.get_active_character(
                interaction.user.id,
                interaction.guild.id
            )
            
            if not char:
                await interaction.response.send_message(
                    "❌ You need a character first! Click 'Create Character' or use `/character create`",
                    ephemeral=True
                )
                return
            
            await self.game_master.bot.db.add_session_player(session_id, char['id'])
            
            await interaction.response.send_message(
                f"✅ **{char['name']}** has joined **{session_name}**! 🎉",
                ephemeral=False
            )
        return callback


class GameMaster(commands.Cog):
    """Main game master functionality - interviews, game flow, DM messaging"""
    
    def __init__(self, bot):
        self.bot = bot
        # Track ongoing character interviews {user_id: interview_state}
        self.active_interviews: Dict[int, Dict[str, Any]] = {}
        # Track active games {session_id: game_state}
        self.active_games: Dict[int, Dict[str, Any]] = {}
    
    @property
    def db(self):
        return self.bot.db
    
    @property
    def llm(self):
        return self.bot.llm
    
    # =========================================================================
    # GAME COMMANDS
    # =========================================================================
    
    game_group = app_commands.Group(name="game", description="Game management commands")
    
    @game_group.command(name="menu", description="Open the game menu - start here!")
    async def game_menu(self, interaction: discord.Interaction):
        """Show the main game menu"""
        embed = discord.Embed(
            title="🎲 RPG Dungeon Master",
            description=(
                "**Welcome, adventurer!**\n\n"
                "Ready to embark on an AI-powered tabletop RPG adventure? "
                "The Dungeon Master awaits to guide you through dangerous dungeons, "
                "mysterious quests, and epic battles!\n\n"
                "**Choose an option below to get started:**"
            ),
            color=discord.Color.gold()
        )
        
        # Check if user has a character
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if char:
            embed.add_field(
                name="👤 Your Character",
                value=f"**{char['name']}** - Level {char['level']} {char['race']} {char['class']}\n❤️ {char['hp']}/{char['max_hp']} HP",
                inline=False
            )
        else:
            embed.add_field(
                name="👤 No Character Yet!",
                value="Create one to start playing!",
                inline=False
            )
        
        # Check for active sessions
        sessions = await self.db.get_sessions(interaction.guild.id, status='active')
        if sessions:
            session_list = "\n".join([f"• **{s['name']}** (ID: {s['id']})" for s in sessions[:3]])
            embed.add_field(
                name="🎮 Active Games",
                value=session_list,
                inline=False
            )
        
        view = QuickStartView(self)
        await interaction.response.send_message(embed=embed, view=view)
    
    @game_group.command(name="start", description="Start a new game session")
    @app_commands.describe(
        name="Name for your game session",
        description="Brief description of the adventure"
    )
    async def start_game(
        self,
        interaction: discord.Interaction,
        name: str,
        description: Optional[str] = None
    ):
        """Create and optionally start a new game"""
        await interaction.response.defer()
        
        # Create session
        session_id = await self.db.create_session(
            guild_id=interaction.guild.id,
            name=name,
            description=description or "A new adventure awaits!",
            dm_user_id=interaction.user.id,
            max_players=6
        )
        
        # Get user's character
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        # DM the session creator
        try:
            dm_channel = await interaction.user.create_dm()
            admin_embed = discord.Embed(
                title="🎭 Game Master Controls",
                description=f"You're running **{name}** (Session #{session_id})",
                color=discord.Color.purple()
            )
            admin_embed.add_field(
                name="Commands",
                value=(
                    f"`/game begin {session_id}` - Start the adventure\n"
                    f"`/game status {session_id}` - View game status\n"
                    f"`/game pause {session_id}` - Pause game\n"
                    f"`/game end {session_id}` - End session"
                ),
                inline=False
            )
            await dm_channel.send(embed=admin_embed)
        except discord.Forbidden:
            pass
        
        if not char:
            embed = discord.Embed(
                title=f"🎲 Game Created: {name}",
                description="You need a character to play! Check your DMs for character creation.",
                color=discord.Color.yellow()
            )
            embed.add_field(name="Session ID", value=str(session_id), inline=True)
            await interaction.followup.send(embed=embed)
            await self.start_character_interview(interaction.user, interaction.guild)
        else:
            await self.db.add_session_player(session_id, char['id'])
            embed = discord.Embed(
                title=f"🎲 Game Created: {name}",
                description=f"**{char['name']}** is ready to adventure!",
                color=discord.Color.green()
            )
            embed.add_field(name="Session ID", value=str(session_id), inline=True)
            embed.add_field(
                name="Next Steps",
                value=f"• Others join with `/game join {session_id}`\n• Begin with `/game begin {session_id}`",
                inline=False
            )
            view = BeginGameView(self, session_id)
            await interaction.followup.send(embed=embed, view=view)
    
    @game_group.command(name="join", description="Join an existing game session")
    @app_commands.describe(session_id="The session ID to join")
    async def join_game(self, interaction: discord.Interaction, session_id: int):
        """Join a game session"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first! Use `/game menu` to create one.",
                ephemeral=True
            )
            return
        
        # Check if already in session
        players = await self.db.get_session_players(session_id)
        if any(p['character_id'] == char['id'] for p in players):
            await interaction.response.send_message(
                f"You're already in **{session['name']}**!",
                ephemeral=True
            )
            return
        
        # Check capacity
        if len(players) >= session['max_players']:
            await interaction.response.send_message("❌ This game is full!", ephemeral=True)
            return
        
        await self.db.add_session_player(session_id, char['id'])
        
        await interaction.response.send_message(
            f"✅ **{char['name']}** has joined **{session['name']}**! 🎉\n"
            f"Party size: {len(players) + 1}/{session['max_players']}"
        )
        
        # Notify the DM
        try:
            dm_user = interaction.guild.get_member(session['dm_user_id'])
            if dm_user:
                dm_channel = await dm_user.create_dm()
                await dm_channel.send(
                    f"🎮 **{char['name']}** ({interaction.user.display_name}) has joined your game **{session['name']}**!"
                )
        except discord.Forbidden:
            pass
    
    @game_group.command(name="begin", description="Begin the adventure! (Game creator only)")
    @app_commands.describe(session_id="The session ID to begin")
    async def begin_game_cmd(self, interaction: discord.Interaction, session_id: int):
        """Begin a game session"""
        await self.begin_game(interaction, session_id)
    
    async def begin_game(self, interaction: discord.Interaction, session_id: int):
        """Actually begin the game with DM narration"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        
        if session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the game creator can begin the adventure!",
                ephemeral=True
            )
            return
        
        players = await self.db.get_session_players(session_id)
        
        if not players:
            await interaction.response.send_message(
                "❌ No players have joined yet! Wait for players or create a character first.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Mark session as active
        await self.db.update_session(session_id, status='active')
        
        # Build party info for the DM
        party_info = []
        for p in players:
            char = await self.db.get_character(p['character_id'])
            if char:
                party_info.append(char)
        
        party_text = "\n".join([
            f"• **{c['name']}** - Level {c['level']} {c['race']} {c['class']}"
            for c in party_info
        ])
        
        # Get the AI DM to introduce the adventure
        if self.llm:
            intro_prompt = self.bot.prompts.get_dm_system_prompt() + f"""

You are now starting a brand new adventure called "{session['name']}".
Description: {session['description'] or 'An adventure awaits!'}

THE PARTY:
{party_text}

INSTRUCTIONS:
1. Welcome the party dramatically
2. Set the opening scene - where are they? What do they see?
3. Introduce an immediate hook or situation that demands their attention
4. End with a question or prompt that invites player action
5. Be vivid and engaging - this is the start of an epic adventure!
6. Keep it to 3-4 paragraphs maximum

Begin the adventure now!"""
            
            try:
                response = await self.llm.chat(
                    messages=[
                        {"role": "system", "content": intro_prompt},
                        {"role": "user", "content": "Begin our adventure!"}
                    ]
                )
                
                dm_intro = response.get('content', '')
            except Exception as e:
                logger.error(f"Error getting DM intro: {e}")
                dm_intro = (
                    "*The mists part to reveal your party standing at the crossroads of fate...*\n\n"
                    f"Welcome, brave adventurers, to **{session['name']}**!\n\n"
                    f"{session['description'] or 'Your journey begins here.'}\n\n"
                    "What would you like to do?"
                )
        else:
            dm_intro = (
                f"⚔️ **{session['name']}** has begun!\n\n"
                f"{session['description'] or 'Your adventure awaits!'}\n\n"
                f"**Party:**\n{party_text}\n\n"
                "@mention me to interact with the Dungeon Master!"
            )
        
        # Create announcement embed
        embed = discord.Embed(
            title=f"⚔️ {session['name']} Begins!",
            description=dm_intro,
            color=discord.Color.gold()
        )
        embed.set_footer(text="@mention the bot or use /dm to interact with the Dungeon Master!")
        
        await interaction.followup.send(embed=embed)
        
        # Store active game state
        self.active_games[session_id] = {
            'session': session,
            'party': party_info,
            'started_at': datetime.utcnow().isoformat(),
            'turn_count': 0
        }
        
        # DM the session creator
        try:
            dm_user = interaction.guild.get_member(session['dm_user_id'])
            if dm_user:
                dm_channel = await dm_user.create_dm()
                await dm_channel.send(
                    f"🎮 **{session['name']}** is now live!\n\n"
                    f"The AI DM will keep things moving. Use `/dm` or `/narrate` to guide the story.\n"
                    f"Use `/game pause {session_id}` if you need a break!"
                )
        except discord.Forbidden:
            pass
    
    @game_group.command(name="status", description="Check game status")
    @app_commands.describe(session_id="The session ID to check (optional)")
    async def game_status(self, interaction: discord.Interaction, session_id: Optional[int] = None):
        """Check game status"""
        if session_id:
            session = await self.db.get_session(session_id)
            if not session:
                await interaction.response.send_message("❌ Game not found!", ephemeral=True)
                return
            sessions = [session]
        else:
            # Get all active sessions in guild
            sessions = await self.db.get_sessions(interaction.guild.id, status='active')
            if not sessions:
                sessions = await self.db.get_sessions(interaction.guild.id, status='inactive')
        
        if not sessions:
            await interaction.response.send_message(
                "No games found! Start one with `/game start`",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎲 Game Status",
            color=discord.Color.blue()
        )
        
        for session in sessions[:5]:
            players = await self.db.get_session_players(session['id'])
            dm = interaction.guild.get_member(session['dm_user_id'])
            
            status_emoji = {"active": "🟢", "paused": "🟡", "inactive": "⚪", "completed": "✅"}.get(session['status'], "⚪")
            
            player_names = []
            for p in players:
                char = await self.db.get_character(p['character_id'])
                if char:
                    player_names.append(f"{char['name']} (Lv.{char['level']})")
            
            embed.add_field(
                name=f"{status_emoji} {session['name']} (ID: {session['id']})",
                value=(
                    f"**Status:** {session['status'].title()}\n"
                    f"**DM:** {dm.display_name if dm else 'Unknown'}\n"
                    f"**Players:** {', '.join(player_names) or 'None'}\n"
                    f"**Capacity:** {len(players)}/{session['max_players']}"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @game_group.command(name="pause", description="Pause the current game (creator only)")
    @app_commands.describe(session_id="The session ID to pause")
    async def pause_game(self, interaction: discord.Interaction, session_id: int):
        """Pause a game"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        
        if session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the game creator can pause the game!",
                ephemeral=True
            )
            return
        
        await self.db.update_session(session_id, status='paused')
        
        await interaction.response.send_message(
            f"⏸️ **{session['name']}** has been paused.\n"
            f"Use `/game begin {session_id}` to resume!"
        )
    
    @game_group.command(name="end", description="End the current game (creator only)")
    @app_commands.describe(session_id="The session ID to end")
    async def end_game(self, interaction: discord.Interaction, session_id: int):
        """End a game"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        
        if session['dm_user_id'] != interaction.user.id:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Only the game creator or an admin can end the game!",
                    ephemeral=True
                )
                return
        
        await self.db.update_session(session_id, status='completed')
        
        # Clean up active game state
        if session_id in self.active_games:
            del self.active_games[session_id]
        
        embed = discord.Embed(
            title=f"🏁 {session['name']} Has Ended",
            description="Thank you for playing! The adventure has concluded.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="What's Next?",
            value="Start a new adventure with `/game start`!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    # =========================================================================
    # CHARACTER INTERVIEW SYSTEM
    # =========================================================================
    
    async def start_character_interview(self, user: discord.User, guild: discord.Guild):
        """Start the character creation interview via DM"""
        try:
            dm_channel = await user.create_dm()
        except discord.Forbidden:
            logger.warning(f"Cannot DM user {user.id}")
            return
        
        # Initialize interview state
        self.active_interviews[user.id] = {
            'guild_id': guild.id,
            'dm_channel': dm_channel,
            'current_field': None,
            'responses': {},
            'stage': 'greeting'
        }
        
        # Send greeting
        embed = discord.Embed(
            title="🎭 Character Creation Interview",
            description=(
                f"Greetings, adventurer! I am the Dungeon Master for **{guild.name}**.\n\n"
                "I'll help you create your character through a brief interview. "
                "Just answer my questions naturally - you can type your responses or use the buttons when available.\n\n"
                "Let's begin!"
            ),
            color=discord.Color.purple()
        )
        
        await dm_channel.send(embed=embed)
        
        # Ask first question
        await asyncio.sleep(1)  # Brief pause for readability
        await self.ask_next_interview_question(user.id)
    
    async def ask_next_interview_question(self, user_id: int):
        """Ask the next question in the interview"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        dm_channel = interview['dm_channel']
        responses = interview['responses']
        
        # Determine next field to ask about
        next_field = None
        for field in ['name', 'race', 'char_class', 'backstory']:
            if field not in responses:
                next_field = field
                break
        
        if next_field is None:
            # Interview complete - create character
            await self.complete_character_interview(user_id)
            return
        
        interview['current_field'] = next_field
        question = REQUIRED_CHARACTER_FIELDS[next_field]
        
        # Create view with buttons for race/class
        view = None
        if next_field in ['race', 'char_class']:
            view = CharacterInterviewView(self, user_id, interview['guild_id'], next_field)
        
        # Use AI to make the question more engaging if available
        if self.llm and next_field == 'backstory':
            char_name = responses.get('name', 'adventurer')
            char_race = responses.get('race', 'unknown')
            char_class = responses.get('char_class', 'unknown')
            
            question = (
                f"Excellent choice! So **{char_name}**, a {char_race} {char_class}...\n\n"
                f"Every hero has a story. What's yours?\n\n"
                f"*Tell me about {char_name}'s past - where they came from, what shaped them, "
                f"or what drove them to become an adventurer. A few sentences is perfect!*"
            )
        
        embed = discord.Embed(
            title=f"📝 Character Creation ({list(REQUIRED_CHARACTER_FIELDS.keys()).index(next_field) + 1}/4)",
            description=question,
            color=discord.Color.blue()
        )
        
        if view:
            await dm_channel.send(embed=embed, view=view)
        else:
            await dm_channel.send(embed=embed)
    
    async def process_interview_response(
        self,
        user_id: int,
        guild_id: int,
        field: str,
        value: str,
        channel: discord.abc.Messageable = None
    ):
        """Process a response to an interview question"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        
        # Validate and store response
        interview['responses'][field] = value
        
        # Send acknowledgment
        dm_channel = channel or interview['dm_channel']
        
        acknowledgments = {
            'name': f"**{value}** - a fine name for a hero!",
            'race': f"A **{value}**! An excellent choice.",
            'char_class': f"The path of the **{value}** - adventurous!",
            'backstory': "A compelling story! The threads of fate weave together..."
        }
        
        await dm_channel.send(acknowledgments.get(field, "Noted!"))
        await asyncio.sleep(0.5)
        
        # Ask next question
        await self.ask_next_interview_question(user_id)
    
    async def complete_character_interview(self, user_id: int):
        """Complete the interview and create the character"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        responses = interview['responses']
        dm_channel = interview['dm_channel']
        guild_id = interview['guild_id']
        
        # Generate stats (use standard array with some randomness)
        import random
        base_stats = [15, 14, 13, 12, 10, 8]
        random.shuffle(base_stats)
        
        stats = {
            'strength': base_stats[0],
            'dexterity': base_stats[1],
            'constitution': base_stats[2],
            'intelligence': base_stats[3],
            'wisdom': base_stats[4],
            'charisma': base_stats[5]
        }
        
        # Create character
        char_id = await self.db.create_character(
            user_id=user_id,
            guild_id=guild_id,
            name=responses['name'],
            race=responses['race'],
            char_class=responses['char_class'],
            stats=stats,
            backstory=responses.get('backstory')
        )
        
        char = await self.db.get_character(char_id)
        
        # Send completion message
        embed = discord.Embed(
            title="🎉 Character Created!",
            description=f"Welcome to the world, **{char['name']}**!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Your Character",
            value=(
                f"**Name:** {char['name']}\n"
                f"**Race:** {char['race']}\n"
                f"**Class:** {char['class']}\n"
                f"**Level:** {char['level']}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="📈 Stats",
            value=(
                f"STR: {char['strength']} | DEX: {char['dexterity']}\n"
                f"CON: {char['constitution']} | INT: {char['intelligence']}\n"
                f"WIS: {char['wisdom']} | CHA: {char['charisma']}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="❤️ Health",
            value=f"{char['hp']}/{char['max_hp']} HP",
            inline=True
        )
        
        if char['backstory']:
            embed.add_field(
                name="📜 Backstory",
                value=char['backstory'][:200] + ("..." if len(char['backstory']) > 200 else ""),
                inline=False
            )
        
        embed.add_field(
            name="🎮 Next Steps",
            value=(
                "Return to the server and:\n"
                "• Join a game with `/game join [id]`\n"
                "• Start your own with `/game start`\n"
                "• View your sheet with `/character sheet`"
            ),
            inline=False
        )
        
        await dm_channel.send(embed=embed)
        
        # Clean up interview state
        del self.active_interviews[user_id]
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for DM responses during character interview"""
        # Ignore bots
        if message.author.bot:
            return
        
        # Only process DMs
        if message.guild is not None:
            return
        
        # Check if user is in an interview
        user_id = message.author.id
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        current_field = interview.get('current_field')
        
        if not current_field:
            return
        
        # Process the response
        await self.process_interview_response(
            user_id,
            interview['guild_id'],
            current_field,
            message.content,
            message.channel
        )
    
    # =========================================================================
    # DM NOTIFICATIONS (Meta/Admin Messages)
    # =========================================================================
    
    async def notify_game_creator(
        self,
        session_id: int,
        title: str,
        message: str,
        color: discord.Color = discord.Color.blue()
    ):
        """Send a notification to the game creator via DM"""
        session = await self.db.get_session(session_id)
        if not session:
            return
        
        try:
            # We need to get the user from any guild they share with the bot
            user = self.bot.get_user(session['dm_user_id'])
            if not user:
                user = await self.bot.fetch_user(session['dm_user_id'])
            
            dm_channel = await user.create_dm()
            
            embed = discord.Embed(
                title=f"🎭 {title}",
                description=f"**Game:** {session['name']}\n\n{message}",
                color=color
            )
            
            await dm_channel.send(embed=embed)
            
        except (discord.Forbidden, discord.NotFound):
            logger.warning(f"Could not notify game creator {session['dm_user_id']}")
    
    async def check_party_status(self, session_id: int) -> Dict[str, Any]:
        """Check the party status and identify any issues"""
        session = await self.db.get_session(session_id)
        if not session:
            return {'error': 'Session not found'}
        
        players = await self.db.get_session_players(session_id)
        
        issues = []
        warnings = []
        
        party_data = []
        for p in players:
            char = await self.db.get_character(p['character_id'])
            if char:
                party_data.append(char)
                
                # Check for issues
                if char['hp'] <= 0:
                    issues.append(f"**{char['name']}** is unconscious/dead!")
                elif char['hp'] < char['max_hp'] * 0.25:
                    warnings.append(f"**{char['name']}** is critically wounded ({char['hp']}/{char['max_hp']} HP)")
        
        return {
            'party': party_data,
            'issues': issues,
            'warnings': warnings,
            'player_count': len(players),
            'max_players': session['max_players']
        }


async def setup(bot):
    await bot.add_cog(GameMaster(bot))
