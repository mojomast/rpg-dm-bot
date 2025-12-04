"""
RPG DM Bot - Sessions Cog
Handles game session management
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger('rpg.sessions')


class SessionView(discord.ui.View):
    """View for session management"""
    
    def __init__(self, bot, session: dict):
        super().__init__(timeout=600)
        self.bot = bot
        self.session = session
    
    @discord.ui.button(label="Join Session", style=discord.ButtonStyle.success, emoji="🎮")
    async def join_session(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Join the game session"""
        char = await self.bot.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character to join! Use `/character create`",
                ephemeral=True
            )
            return
        
        await self.bot.db.add_session_player(self.session['id'], char['id'])
        
        await interaction.response.send_message(
            f"✅ **{char['name']}** has joined the session!",
            ephemeral=False
        )
    
    @discord.ui.button(label="Leave Session", style=discord.ButtonStyle.danger, emoji="🚪")
    async def leave_session(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Leave the game session"""
        char = await self.bot.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        await self.bot.db.remove_session_player(self.session['id'], char['id'])
        
        await interaction.response.send_message(
            f"👋 **{char['name']}** has left the session.",
            ephemeral=False
        )
    
    @discord.ui.button(label="View Players", style=discord.ButtonStyle.secondary, emoji="👥")
    async def view_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View session players"""
        players = await self.bot.db.get_session_players(self.session['id'])
        
        if not players:
            await interaction.response.send_message(
                "No players have joined yet!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"👥 Players in {self.session['name']}",
            color=discord.Color.blue()
        )
        
        for player in players:
            char = await self.bot.db.get_character(player['character_id'])
            if char:
                char_class = char.get('char_class') or char.get('class', 'Unknown')
                embed.add_field(
                    name=char['name'],
                    value=f"Level {char['level']} {char['race']} {char_class}",
                    inline=True
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CreateSessionModal(discord.ui.Modal, title="Create New Session"):
    """Modal for creating a game session"""
    
    session_name = discord.ui.TextInput(
        label="Session Name",
        placeholder="The Adventure Begins",
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.paragraph,
        placeholder="What is this session about?",
        max_length=500,
        required=False
    )
    
    max_players = discord.ui.TextInput(
        label="Max Players",
        placeholder="6",
        max_length=2,
        required=False
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        max_p = 6
        if self.max_players.value:
            try:
                max_p = int(self.max_players.value)
            except ValueError:
                pass
        
        session_id = await self.bot.db.create_session(
            guild_id=interaction.guild.id,
            name=str(self.session_name),
            description=str(self.description) if self.description.value else "",
            dm_user_id=interaction.user.id,
            max_players=max_p
        )
        
        session = await self.bot.db.get_session(session_id)
        
        embed = discord.Embed(
            title=f"🎲 Session Created: {self.session_name}",
            description=str(self.description) if self.description.value else "A new adventure awaits!",
            color=discord.Color.green()
        )
        embed.add_field(name="Dungeon Master", value=interaction.user.mention, inline=True)
        embed.add_field(name="Max Players", value=str(max_p), inline=True)
        embed.add_field(name="Session ID", value=str(session_id), inline=True)
        embed.add_field(
            name="How to Join",
            value="Click the **Join Session** button below!",
            inline=False
        )
        
        view = SessionView(self.bot, session)
        await interaction.response.send_message(embed=embed, view=view)


class Sessions(commands.Cog):
    """Game session management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    session_group = app_commands.Group(
        name="session", 
        description="Session commands",
        guild_only=True
    )
    
    @session_group.command(name="create", description="Create a new game session")
    async def create_session(self, interaction: discord.Interaction):
        """Create a new game session"""
        modal = CreateSessionModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @session_group.command(name="list", description="List all sessions")
    @app_commands.describe(status="Filter by status")
    @app_commands.choices(status=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Active", value="active"),
        app_commands.Choice(name="Paused", value="paused"),
        app_commands.Choice(name="Completed", value="completed"),
    ])
    async def list_sessions(
        self,
        interaction: discord.Interaction,
        status: str = "all"
    ):
        """List available sessions"""
        sessions = await self.db.get_sessions(
            interaction.guild.id,
            status=None if status == "all" else status
        )
        
        if not sessions:
            await interaction.response.send_message(
                "📜 No sessions found! Create one with `/session create`",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎲 Game Sessions",
            description="Available sessions:",
            color=discord.Color.blue()
        )
        
        for session in sessions[:10]:
            status_emoji = {
                "active": "🟢",
                "paused": "🟡",
                "completed": "✅"
            }.get(session['status'], "⚪")
            
            dm = interaction.guild.get_member(session['dm_user_id'])
            dm_name = dm.display_name if dm else "Unknown"
            
            players = await self.db.get_session_players(session['id'])
            player_count = len(players)
            
            embed.add_field(
                name=f"{status_emoji} [{session['id']}] {session['name']}",
                value=f"DM: {dm_name}\nPlayers: {player_count}/{session['max_players']}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    @session_group.command(name="view", description="View session details")
    @app_commands.describe(session_id="The ID of the session")
    async def view_session(self, interaction: discord.Interaction, session_id: int):
        """View session details"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message(
                "❌ Session not found!",
                ephemeral=True
            )
            return
        
        dm = interaction.guild.get_member(session['dm_user_id'])
        players = await self.db.get_session_players(session['id'])
        
        embed = discord.Embed(
            title=f"🎲 {session['name']}",
            description=session['description'] or "No description.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Dungeon Master",
            value=dm.mention if dm else "Unknown",
            inline=True
        )
        embed.add_field(
            name="Status",
            value=session['status'].title(),
            inline=True
        )
        embed.add_field(
            name="Players",
            value=f"{len(players)}/{session['max_players']}",
            inline=True
        )
        
        if session.get('current_quest_id'):
            quest = await self.db.get_quest(session['current_quest_id'])
            if quest:
                embed.add_field(
                    name="Current Quest",
                    value=quest['title'],
                    inline=False
                )
        
        # List players
        if players:
            player_list = []
            for player in players:
                char = await self.db.get_character(player['character_id'])
                if char:
                    char_class = char.get('char_class') or char.get('class', 'Unknown')
                    player_list.append(f"• {char['name']} (Lv.{char['level']} {char_class})")
            if player_list:
                embed.add_field(
                    name="Party Members",
                    value="\n".join(player_list),
                    inline=False
                )
        
        view = SessionView(self.bot, session)
        await interaction.response.send_message(embed=embed, view=view)
    
    @session_group.command(name="join", description="Join a game session")
    @app_commands.describe(session_id="The ID of the session to join")
    async def join_session(self, interaction: discord.Interaction, session_id: int):
        """Join a session"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message(
                "❌ Session not found!",
                ephemeral=True
            )
            return
        
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character! Use `/character create`",
                ephemeral=True
            )
            return
        
        players = await self.db.get_session_players(session['id'])
        if len(players) >= session['max_players']:
            await interaction.response.send_message(
                "❌ This session is full!",
                ephemeral=True
            )
            return
        
        await self.db.add_session_player(session['id'], char['id'])
        
        await interaction.response.send_message(
            f"✅ **{char['name']}** has joined **{session['name']}**!"
        )
    
    @session_group.command(name="leave", description="Leave a game session")
    @app_commands.describe(session_id="The ID of the session to leave")
    async def leave_session(self, interaction: discord.Interaction, session_id: int):
        """Leave a session"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message(
                "❌ Session not found!",
                ephemeral=True
            )
            return
        
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        await self.db.remove_session_player(session['id'], char['id'])
        
        await interaction.response.send_message(
            f"👋 **{char['name']}** has left **{session['name']}**."
        )
    
    @session_group.command(name="start", description="Start a session (DM only)")
    @app_commands.describe(session_id="The ID of the session to start")
    async def start_session(self, interaction: discord.Interaction, session_id: int):
        """Start a session"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message(
                "❌ Session not found!",
                ephemeral=True
            )
            return
        
        if session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the Dungeon Master can start the session!",
                ephemeral=True
            )
            return
        
        await self.db.update_session(session_id, status='active')
        
        players = await self.db.get_session_players(session_id)
        
        embed = discord.Embed(
            title=f"⚔️ {session['name']} Has Begun!",
            description="The adventure starts now! May fortune favor the brave.",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Party Size",
            value=f"{len(players)} adventurers",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    @session_group.command(name="pause", description="Pause a session (DM only)")
    @app_commands.describe(session_id="The ID of the session to pause")
    async def pause_session(self, interaction: discord.Interaction, session_id: int):
        """Pause a session"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message(
                "❌ Session not found!",
                ephemeral=True
            )
            return
        
        if session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the DM can pause the session!",
                ephemeral=True
            )
            return
        
        await self.db.update_session(session_id, status='paused')
        
        await interaction.response.send_message(
            f"⏸️ **{session['name']}** has been paused."
        )
    
    @session_group.command(name="end", description="End a session (DM only)")
    @app_commands.describe(session_id="The ID of the session to end")
    async def end_session(self, interaction: discord.Interaction, session_id: int):
        """End a session"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message(
                "❌ Session not found!",
                ephemeral=True
            )
            return
        
        if session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the DM can end the session!",
                ephemeral=True
            )
            return
        
        await self.db.update_session(session_id, status='completed')
        
        embed = discord.Embed(
            title=f"🏁 {session['name']} Has Ended",
            description="Thank you for playing! Until next time, adventurers.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @session_group.command(name="set_quest", description="Set the active quest for a session (DM only)")
    @app_commands.describe(
        session_id="The session ID",
        quest_id="The quest ID to set as active"
    )
    async def set_quest(
        self,
        interaction: discord.Interaction,
        session_id: int,
        quest_id: int
    ):
        """Set active quest for session"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message(
                "❌ Session not found!",
                ephemeral=True
            )
            return
        
        if session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the DM can set the quest!",
                ephemeral=True
            )
            return
        
        quest = await self.db.get_quest(quest_id)
        if not quest:
            await interaction.response.send_message(
                "❌ Quest not found!",
                ephemeral=True
            )
            return
        
        await self.db.update_session(session_id, current_quest_id=quest_id)
        
        await interaction.response.send_message(
            f"✅ **{session['name']}** is now on quest: **{quest['title']}**"
        )
    
    @session_group.command(name="delete", description="Delete a session (DM only)")
    @app_commands.describe(session_id="The ID of the session to delete")
    async def delete_session(self, interaction: discord.Interaction, session_id: int):
        """Delete a session"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message(
                "❌ Session not found!",
                ephemeral=True
            )
            return
        
        if session['dm_user_id'] != interaction.user.id:
            # Check if admin
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Only the DM or an admin can delete this session!",
                    ephemeral=True
                )
                return
        
        await self.db.delete_session(session_id)
        
        await interaction.response.send_message(
            f"🗑️ Session **{session['name']}** has been deleted."
        )


async def setup(bot):
    await bot.add_cog(Sessions(bot))
