"""
RPG DM Bot - Quests Cog
Handles quest creation, management, and progression
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
from datetime import datetime

logger = logging.getLogger('rpg.quests')

# Quest difficulty settings
QUEST_DIFFICULTIES = {
    "easy": {"xp_mult": 1.0, "gold_mult": 1.0},
    "medium": {"xp_mult": 1.5, "gold_mult": 1.5},
    "hard": {"xp_mult": 2.0, "gold_mult": 2.0},
    "legendary": {"xp_mult": 3.0, "gold_mult": 3.0}
}

# Base rewards
BASE_QUEST_XP = 100
BASE_QUEST_GOLD = 50


class QuestView(discord.ui.View):
    """View for displaying quest details"""
    
    def __init__(self, bot, quest: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.quest = quest
    
    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"📜 {self.quest['title']}",
            description=self.quest['description'],
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Status",
            value=self.quest['status'].replace('_', ' ').title(),
            inline=True
        )
        embed.add_field(
            name="Difficulty",
            value=self.quest['difficulty'].title(),
            inline=True
        )
        
        objectives = self.quest.get('objectives', [])
        if objectives:
            obj_text = "\n".join([f"• {obj.get('description', obj) if isinstance(obj, dict) else obj}" for obj in objectives])
            embed.add_field(name="Objectives", value=obj_text[:1000], inline=False)
        
        rewards = self.quest.get('rewards', {})
        if rewards:
            reward_text = []
            if rewards.get('xp'):
                reward_text.append(f"✨ {rewards['xp']} XP")
            if rewards.get('gold'):
                reward_text.append(f"💰 {rewards['gold']} Gold")
            if rewards.get('items'):
                reward_text.append(f"🎁 Items: {', '.join(rewards['items'])}")
            if reward_text:
                embed.add_field(name="Rewards", value="\n".join(reward_text), inline=False)
        
        return embed


class CreateQuestModal(discord.ui.Modal, title="Create New Quest"):
    """Modal for creating a new quest"""
    
    quest_title = discord.ui.TextInput(
        label="Quest Title",
        placeholder="The Dragon's Lair",
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Quest Description",
        style=discord.TextStyle.paragraph,
        placeholder="Describe the quest and its background...",
        max_length=1000
    )
    
    objectives_text = discord.ui.TextInput(
        label="Objectives (one per line)",
        style=discord.TextStyle.paragraph,
        placeholder="Find the cave entrance\nDefeat the dragon guardian\nRetrieve the ancient artifact",
        max_length=1000
    )
    
    rewards_text = discord.ui.TextInput(
        label="Rewards (format: XP:100, Gold:50)",
        placeholder="XP:200, Gold:100",
        max_length=200,
        required=False
    )
    
    def __init__(self, bot, difficulty: str):
        super().__init__()
        self.bot = bot
        self.difficulty = difficulty
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse objectives
        objectives = [
            {"description": line.strip(), "completed": False}
            for line in self.objectives_text.value.strip().split('\n')
            if line.strip()
        ]
        
        # Parse rewards
        rewards = {}
        if self.rewards_text.value:
            for part in self.rewards_text.value.split(','):
                if ':' in part:
                    key, val = part.split(':', 1)
                    key = key.strip().lower()
                    try:
                        rewards[key] = int(val.strip())
                    except ValueError:
                        rewards[key] = val.strip()
        
        # Apply difficulty multipliers
        diff = QUEST_DIFFICULTIES.get(self.difficulty, QUEST_DIFFICULTIES['medium'])
        if not rewards.get('xp'):
            rewards['xp'] = int(BASE_QUEST_XP * diff['xp_mult'])
        if not rewards.get('gold'):
            rewards['gold'] = int(BASE_QUEST_GOLD * diff['gold_mult'])
        
        # Create quest
        quest_id = await self.bot.db.create_quest(
            guild_id=interaction.guild.id,
            title=str(self.quest_title),
            description=str(self.description),
            objectives=objectives,
            rewards=rewards,
            difficulty=self.difficulty,
            created_by=interaction.user.id
        )
        
        embed = discord.Embed(
            title="✅ Quest Created!",
            description=f"**{self.quest_title}**\n\n{self.description}",
            color=discord.Color.green()
        )
        embed.add_field(name="Difficulty", value=self.difficulty.title(), inline=True)
        embed.add_field(name="Objectives", value=str(len(objectives)), inline=True)
        embed.add_field(name="Quest ID", value=str(quest_id), inline=True)
        embed.add_field(name="Rewards", value=f"XP: {rewards.get('xp', 0)}, Gold: {rewards.get('gold', 0)}", inline=False)
        
        await interaction.response.send_message(embed=embed)


class Quests(commands.Cog):
    """Quest management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    quest_group = app_commands.Group(
        name="quest", 
        description="Quest commands",
        guild_only=True
    )
    
    @quest_group.command(name="create", description="Create a new quest (DM only)")
    @app_commands.describe(difficulty="Quest difficulty level")
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="Easy", value="easy"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Hard", value="hard"),
        app_commands.Choice(name="Legendary", value="legendary"),
    ])
    async def create_quest(
        self,
        interaction: discord.Interaction,
        difficulty: str = "medium"
    ):
        """Create a new quest"""
        modal = CreateQuestModal(self.bot, difficulty)
        await interaction.response.send_modal(modal)
    
    @quest_group.command(name="list", description="List all quests")
    @app_commands.describe(status="Filter by status")
    @app_commands.choices(status=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Available", value="available"),
        app_commands.Choice(name="In Progress", value="in_progress"),
        app_commands.Choice(name="Completed", value="completed"),
    ])
    async def list_quests(
        self,
        interaction: discord.Interaction,
        status: str = "all"
    ):
        """List available quests"""
        quests = await self.db.get_quests(
            interaction.guild.id,
            status=None if status == "all" else status
        )
        
        if not quests:
            await interaction.response.send_message(
                "📜 No quests found!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📜 Quest Board",
            description="Available quests:",
            color=discord.Color.gold()
        )
        
        for quest in quests[:10]:  # Limit to 10
            status_emoji = {
                "available": "🟢",
                "in_progress": "🟡",
                "completed": "✅",
                "failed": "❌"
            }.get(quest['status'], "⚪")
            
            obj_count = len(quest.get('objectives', []))
            
            embed.add_field(
                name=f"{status_emoji} [{quest['id']}] {quest['title']}",
                value=f"Difficulty: {quest['difficulty'].title()} | Objectives: {obj_count}\n{quest['description'][:80]}...",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @quest_group.command(name="view", description="View quest details")
    @app_commands.describe(quest_id="The ID of the quest to view")
    async def view_quest(self, interaction: discord.Interaction, quest_id: int):
        """View detailed quest information"""
        quest = await self.db.get_quest(quest_id)
        
        if not quest:
            await interaction.response.send_message(
                "❌ Quest not found!",
                ephemeral=True
            )
            return
        
        view = QuestView(self.bot, quest)
        await interaction.response.send_message(embed=view.get_embed(), view=view)
    
    @quest_group.command(name="accept", description="Accept a quest")
    @app_commands.describe(quest_id="The ID of the quest to accept")
    async def accept_quest(self, interaction: discord.Interaction, quest_id: int):
        """Accept a quest for your character"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character! Use `/character create`",
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
        
        if quest['status'] != 'available':
            await interaction.response.send_message(
                f"❌ This quest is not available (status: {quest['status']})!",
                ephemeral=True
            )
            return
        
        result = await self.db.accept_quest(quest_id, char['id'])
        
        if 'error' in result:
            await interaction.response.send_message(
                f"❌ {result['error']}",
                ephemeral=True
            )
            return
        
        # Update quest status
        await self.db.update_quest(quest_id, status='in_progress')
        
        embed = discord.Embed(
            title=f"⚔️ Quest Accepted: {quest['title']}",
            description=f"**{char['name']}** has accepted the quest!\n\n{quest['description']}",
            color=discord.Color.green()
        )
        
        objectives = quest.get('objectives', [])
        if objectives:
            obj_text = "\n".join([f"☐ {obj.get('description', obj) if isinstance(obj, dict) else obj}" for obj in objectives])
            embed.add_field(name="Objectives", value=obj_text[:1000], inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @quest_group.command(name="progress", description="View your quest progress")
    async def view_progress(self, interaction: discord.Interaction):
        """View your active quests and progress"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character!",
                ephemeral=True
            )
            return
        
        quests = await self.db.get_character_quests(char['id'], status='active')
        
        if not quests:
            await interaction.response.send_message(
                "📜 You have no active quests! Use `/quest list` to find quests.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📋 {char['name']}'s Active Quests",
            color=discord.Color.blue()
        )
        
        for quest in quests[:5]:
            objectives = quest.get('objectives', [])
            completed = quest.get('objectives_completed', [])
            
            progress_text = []
            for i, obj in enumerate(objectives):
                desc = obj.get('description', obj) if isinstance(obj, dict) else obj
                status = "✅" if i in completed else "☐"
                progress_text.append(f"{status} {desc}")
            
            embed.add_field(
                name=f"[{quest['id']}] {quest['title']}",
                value="\n".join(progress_text)[:1000] or "No objectives",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @quest_group.command(name="complete_objective", description="Mark an objective as complete (DM only)")
    @app_commands.describe(
        quest_id="The ID of the quest",
        objective_num="The objective number (starting from 1)",
        player="The player who completed it"
    )
    async def complete_objective(
        self,
        interaction: discord.Interaction,
        quest_id: int,
        objective_num: int,
        player: discord.Member
    ):
        """Mark a quest objective as complete for a player"""
        char = await self.db.get_active_character(player.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                f"❌ {player.display_name} doesn't have a character!",
                ephemeral=True
            )
            return
        
        result = await self.db.complete_objective(quest_id, char['id'], objective_num - 1)
        
        if 'error' in result:
            await interaction.response.send_message(
                f"❌ {result['error']}",
                ephemeral=True
            )
            return
        
        quest = await self.db.get_quest(quest_id)
        objectives = quest.get('objectives', [])
        obj_desc = objectives[objective_num - 1] if objective_num <= len(objectives) else "Unknown"
        if isinstance(obj_desc, dict):
            obj_desc = obj_desc.get('description', 'Unknown')
        
        embed = discord.Embed(
            title="✅ Objective Complete!",
            description=f"**{char['name']}** completed: {obj_desc}",
            color=discord.Color.green()
        )
        
        if result.get('quest_complete'):
            embed.add_field(
                name="🎉 Quest Complete!",
                value=f"All objectives for **{quest['title']}** have been completed!",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @quest_group.command(name="complete", description="Mark a quest as completed (DM only)")
    @app_commands.describe(quest_id="The ID of the quest to complete")
    async def complete_quest(self, interaction: discord.Interaction, quest_id: int):
        """Mark quest as complete and show rewards"""
        quest = await self.db.get_quest(quest_id)
        
        if not quest:
            await interaction.response.send_message(
                "❌ Quest not found!",
                ephemeral=True
            )
            return
        
        await self.db.update_quest(quest_id, status='completed')
        
        rewards = quest.get('rewards', {})
        
        embed = discord.Embed(
            title=f"🎉 Quest Complete: {quest['title']}",
            description="The quest has been successfully completed!",
            color=discord.Color.gold()
        )
        
        if rewards:
            reward_text = []
            if rewards.get('xp'):
                reward_text.append(f"✨ {rewards['xp']} XP")
            if rewards.get('gold'):
                reward_text.append(f"💰 {rewards['gold']} Gold")
            embed.add_field(name="Rewards (each)", value="\n".join(reward_text) or "None", inline=False)
        
        embed.add_field(
            name="Note",
            value="Use `/character reward` to distribute rewards to participants!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @quest_group.command(name="fail", description="Mark a quest as failed (DM only)")
    @app_commands.describe(quest_id="The ID of the quest to fail")
    async def fail_quest(self, interaction: discord.Interaction, quest_id: int):
        """Mark quest as failed"""
        quest = await self.db.get_quest(quest_id)
        
        if not quest:
            await interaction.response.send_message(
                "❌ Quest not found!",
                ephemeral=True
            )
            return
        
        await self.db.update_quest(quest_id, status='failed')
        
        embed = discord.Embed(
            title=f"💀 Quest Failed: {quest['title']}",
            description="The quest has been marked as failed.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @quest_group.command(name="reset", description="Reset a quest to available (DM only)")
    @app_commands.describe(quest_id="The ID of the quest to reset")
    async def reset_quest(self, interaction: discord.Interaction, quest_id: int):
        """Reset a quest to available state"""
        quest = await self.db.get_quest(quest_id)
        
        if not quest:
            await interaction.response.send_message(
                "❌ Quest not found!",
                ephemeral=True
            )
            return
        
        await self.db.update_quest(quest_id, status='available')
        
        await interaction.response.send_message(
            f"✅ Quest **{quest['title']}** has been reset!"
        )
    
    @quest_group.command(name="delete", description="Delete a quest (DM only)")
    @app_commands.describe(quest_id="The ID of the quest to delete")
    async def delete_quest(self, interaction: discord.Interaction, quest_id: int):
        """Delete a quest"""
        quest = await self.db.get_quest(quest_id)
        
        if not quest:
            await interaction.response.send_message(
                "❌ Quest not found!",
                ephemeral=True
            )
            return
        
        await self.db.delete_quest(quest_id)
        
        await interaction.response.send_message(
            f"🗑️ Quest **{quest['title']}** has been deleted!"
        )


async def setup(bot):
    await bot.add_cog(Quests(bot))
