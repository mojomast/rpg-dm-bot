"""
RPG DM Bot - Character Cog
Handles character creation, management, and progression
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
import logging
import random

logger = logging.getLogger('rpg.characters')

# Available races and classes
RACES = ["Human", "Elf", "Dwarf", "Halfling", "Orc", "Tiefling", "Dragonborn", "Gnome"]
CLASSES = ["Warrior", "Mage", "Rogue", "Cleric", "Ranger", "Bard", "Paladin", "Warlock"]

# Stat rolling methods
STAT_METHODS = {
    "standard": [15, 14, 13, 12, 10, 8],  # Standard array
    "point_buy": None,  # 27 points
    "roll": None,  # 4d6 drop lowest
}


class CharacterCreationModal(discord.ui.Modal, title="Create Your Character"):
    """Modal for character creation"""
    
    name = discord.ui.TextInput(
        label="Character Name",
        placeholder="Enter your character's name...",
        min_length=2,
        max_length=32,
        required=True
    )
    
    backstory = discord.ui.TextInput(
        label="Backstory (Optional)",
        placeholder="Tell us about your character's past...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )
    
    def __init__(self, race: str, char_class: str, stats: dict):
        super().__init__()
        self.race = race
        self.char_class = char_class
        self.stats = stats
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Get database
        db = interaction.client.db
        
        # Create the character
        char_id = await db.create_character(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            name=self.name.value,
            race=self.race,
            char_class=self.char_class,
            stats=self.stats,
            backstory=self.backstory.value if self.backstory.value else None
        )
        
        # Get the created character
        char = await db.get_character(char_id)
        
        # Build response embed
        embed = discord.Embed(
            title=f"🎭 Character Created: {char['name']}",
            description=f"Welcome, {char['name']} the {char['race']} {char['class']}!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Stats",
            value=f"STR: {char['strength']} | DEX: {char['dexterity']} | CON: {char['constitution']}\n"
                  f"INT: {char['intelligence']} | WIS: {char['wisdom']} | CHA: {char['charisma']}",
            inline=False
        )
        
        embed.add_field(name="❤️ HP", value=f"{char['hp']}/{char['max_hp']}", inline=True)
        embed.add_field(name="✨ Mana", value=f"{char['mana']}/{char['max_mana']}", inline=True)
        embed.add_field(name="💰 Gold", value=str(char['gold']), inline=True)
        
        if char['backstory']:
            embed.add_field(name="📜 Backstory", value=char['backstory'][:200], inline=False)
        
        embed.set_footer(text=f"Character ID: {char_id}")
        
        await interaction.followup.send(embed=embed)


class StatAllocationView(discord.ui.View):
    """View for allocating stats during character creation"""
    
    def __init__(self, race: str, char_class: str):
        super().__init__(timeout=300)
        self.race = race
        self.char_class = char_class
        self.stats = {
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10
        }
        self.available_points = [15, 14, 13, 12, 10, 8]  # Standard array
        self.assignments = {}
    
    def get_stat_display(self) -> str:
        lines = []
        for stat in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
            assigned = self.assignments.get(stat, "-")
            lines.append(f"{stat.upper()[:3]}: {assigned}")
        return "\n".join(lines)
    
    def get_available_display(self) -> str:
        return ", ".join(str(p) for p in sorted(self.available_points, reverse=True))
    
    @discord.ui.button(label="Roll Stats (4d6kh3)", style=discord.ButtonStyle.primary)
    async def roll_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Roll 4d6 drop lowest for each stat"""
        for stat in self.stats:
            rolls = sorted([random.randint(1, 6) for _ in range(4)], reverse=True)
            self.stats[stat] = sum(rolls[:3])
            self.assignments[stat] = self.stats[stat]
        
        self.available_points = []
        
        embed = discord.Embed(
            title="🎲 Stats Rolled!",
            description=f"**{self.race} {self.char_class}**\n\n{self.get_stat_display()}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Next Step", value="Click 'Confirm & Create' to finalize your character!")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Standard Array", style=discord.ButtonStyle.secondary)
    async def standard_array(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Use standard array"""
        self.available_points = [15, 14, 13, 12, 10, 8]
        self.assignments = {}
        
        embed = discord.Embed(
            title="📊 Standard Array",
            description=f"**{self.race} {self.char_class}**\n\nAssign these values to your stats:\n**{self.get_available_display()}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Current Stats", value=self.get_stat_display(), inline=True)
        embed.add_field(name="Available", value=self.get_available_display() or "All assigned!", inline=True)
        
        # Add stat assignment select
        select = StatSelect(self)
        self.add_item(select)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Confirm & Create", style=discord.ButtonStyle.success)
    async def confirm_create(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and open name modal"""
        # Finalize stats
        for stat in self.stats:
            if stat in self.assignments:
                self.stats[stat] = self.assignments[stat]
        
        modal = CharacterCreationModal(self.race, self.char_class, self.stats)
        await interaction.response.send_modal(modal)


class StatSelect(discord.ui.Select):
    """Select menu for assigning stats"""
    
    def __init__(self, parent_view: StatAllocationView):
        self.parent_view = parent_view
        
        options = [
            discord.SelectOption(label="Strength", value="strength", emoji="💪"),
            discord.SelectOption(label="Dexterity", value="dexterity", emoji="🏃"),
            discord.SelectOption(label="Constitution", value="constitution", emoji="❤️"),
            discord.SelectOption(label="Intelligence", value="intelligence", emoji="🧠"),
            discord.SelectOption(label="Wisdom", value="wisdom", emoji="👁️"),
            discord.SelectOption(label="Charisma", value="charisma", emoji="✨"),
        ]
        
        super().__init__(placeholder="Select a stat to assign...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        stat = self.values[0]
        
        if not self.parent_view.available_points:
            await interaction.response.send_message("No more points to assign!", ephemeral=True)
            return
        
        # Assign highest available point to selected stat
        value = max(self.parent_view.available_points)
        self.parent_view.available_points.remove(value)
        self.parent_view.assignments[stat] = value
        
        embed = discord.Embed(
            title="📊 Standard Array",
            description=f"**{self.parent_view.race} {self.parent_view.char_class}**\n\nAssigned {value} to {stat.upper()}!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Current Stats", value=self.parent_view.get_stat_display(), inline=True)
        embed.add_field(name="Available", value=self.parent_view.get_available_display() or "All assigned!", inline=True)
        
        await interaction.response.edit_message(embed=embed)


class Characters(commands.Cog):
    """Character management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    character_group = app_commands.Group(name="character", description="Character management commands")
    
    @character_group.command(name="create", description="Create a new character")
    @app_commands.describe(
        race="Choose your character's race",
        char_class="Choose your character's class"
    )
    @app_commands.choices(
        race=[app_commands.Choice(name=r, value=r.lower()) for r in RACES],
        char_class=[app_commands.Choice(name=c, value=c.lower()) for c in CLASSES]
    )
    async def create_character(
        self,
        interaction: discord.Interaction,
        race: str,
        char_class: str
    ):
        """Start character creation process"""
        embed = discord.Embed(
            title="🎭 Character Creation",
            description=f"Creating a **{race.title()} {char_class.title()}**\n\nChoose how to determine your stats:",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🎲 Roll Stats",
            value="Roll 4d6, drop lowest for each stat. Exciting and random!",
            inline=False
        )
        embed.add_field(
            name="📊 Standard Array",
            value="Assign values: 15, 14, 13, 12, 10, 8 to your stats.",
            inline=False
        )
        
        view = StatAllocationView(race.title(), char_class.title())
        await interaction.response.send_message(embed=embed, view=view)
    
    @character_group.command(name="sheet", description="View your character sheet")
    async def character_sheet(self, interaction: discord.Interaction):
        """Display character sheet"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character yet! Use `/character create` to make one.",
                ephemeral=True
            )
            return
        
        # Get equipped items
        equipped = await self.db.get_equipped_items(char['id'])
        equipped_str = "\n".join([f"• {i['item_name']} ({i['slot']})" for i in equipped]) or "Nothing equipped"
        
        # Calculate stat modifiers
        def mod(stat):
            m = (stat - 10) // 2
            return f"+{m}" if m >= 0 else str(m)
        
        embed = discord.Embed(
            title=f"📜 {char['name']}",
            description=f"Level {char['level']} {char['race']} {char['class']}",
            color=discord.Color.gold()
        )
        
        # Health and resources
        hp_bar = "█" * int(char['hp'] / char['max_hp'] * 10) + "░" * (10 - int(char['hp'] / char['max_hp'] * 10))
        embed.add_field(
            name="❤️ Health",
            value=f"{hp_bar}\n{char['hp']}/{char['max_hp']} HP",
            inline=True
        )
        
        if char['max_mana'] > 0:
            mana_bar = "█" * int(char['mana'] / char['max_mana'] * 10) + "░" * (10 - int(char['mana'] / char['max_mana'] * 10))
            embed.add_field(
                name="✨ Mana",
                value=f"{mana_bar}\n{char['mana']}/{char['max_mana']} MP",
                inline=True
            )
        
        embed.add_field(name="💰 Gold", value=str(char['gold']), inline=True)
        
        # Stats
        stats_text = (
            f"**STR:** {char['strength']} ({mod(char['strength'])})\n"
            f"**DEX:** {char['dexterity']} ({mod(char['dexterity'])})\n"
            f"**CON:** {char['constitution']} ({mod(char['constitution'])})\n"
            f"**INT:** {char['intelligence']} ({mod(char['intelligence'])})\n"
            f"**WIS:** {char['wisdom']} ({mod(char['wisdom'])})\n"
            f"**CHA:** {char['charisma']} ({mod(char['charisma'])})"
        )
        embed.add_field(name="📊 Attributes", value=stats_text, inline=True)
        
        # Experience
        xp_thresholds = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000]
        next_level_xp = xp_thresholds[char['level']] if char['level'] < len(xp_thresholds) else "MAX"
        embed.add_field(
            name="⭐ Experience",
            value=f"{char['experience']} / {next_level_xp} XP",
            inline=True
        )
        
        # Equipment
        embed.add_field(name="⚔️ Equipment", value=equipped_str, inline=False)
        
        # Backstory
        if char['backstory']:
            embed.add_field(
                name="📖 Backstory",
                value=char['backstory'][:200] + ("..." if len(char['backstory']) > 200 else ""),
                inline=False
            )
        
        embed.set_footer(text=f"Character ID: {char['id']}")
        
        await interaction.response.send_message(embed=embed)
    
    @character_group.command(name="list", description="List all your characters")
    async def list_characters(self, interaction: discord.Interaction):
        """List all characters for the user"""
        characters = await self.db.get_user_characters(interaction.user.id, interaction.guild.id)
        
        if not characters:
            await interaction.response.send_message(
                "❌ You don't have any characters! Use `/character create` to make one.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎭 Your Characters",
            color=discord.Color.blue()
        )
        
        for char in characters:
            active = "✅ " if char['is_active'] else ""
            embed.add_field(
                name=f"{active}{char['name']}",
                value=f"Level {char['level']} {char['race']} {char['class']}\n"
                      f"HP: {char['hp']}/{char['max_hp']} | Gold: {char['gold']}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    @character_group.command(name="switch", description="Switch your active character")
    @app_commands.describe(character_id="The ID of the character to switch to")
    async def switch_character(self, interaction: discord.Interaction, character_id: int):
        """Switch active character"""
        # Verify the character belongs to the user
        char = await self.db.get_character(character_id)
        
        if not char or char['user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Character not found or doesn't belong to you.",
                ephemeral=True
            )
            return
        
        await self.db.set_active_character(interaction.user.id, interaction.guild.id, character_id)
        
        await interaction.response.send_message(
            f"✅ Switched to **{char['name']}** the {char['race']} {char['class']}!"
        )
    
    @character_group.command(name="levelup", description="Level up your character (if eligible)")
    async def level_up(self, interaction: discord.Interaction):
        """Level up the character if they have enough XP"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        xp_thresholds = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000]
        
        if char['level'] >= len(xp_thresholds):
            await interaction.response.send_message(
                f"🎉 {char['name']} is already at maximum level!",
                ephemeral=True
            )
            return
        
        required_xp = xp_thresholds[char['level']]
        
        if char['experience'] < required_xp:
            await interaction.response.send_message(
                f"❌ {char['name']} needs {required_xp - char['experience']} more XP to level up.\n"
                f"Current: {char['experience']} / {required_xp}",
                ephemeral=True
            )
            return
        
        # Level up!
        new_level = char['level'] + 1
        con_mod = (char['constitution'] - 10) // 2
        hp_increase = max(1, 5 + con_mod)
        
        await self.db.update_character(
            char['id'],
            level=new_level,
            max_hp=char['max_hp'] + hp_increase,
            hp=char['hp'] + hp_increase  # Heal on level up
        )
        
        embed = discord.Embed(
            title="🎉 LEVEL UP!",
            description=f"**{char['name']}** is now level {new_level}!",
            color=discord.Color.gold()
        )
        embed.add_field(name="❤️ HP Increase", value=f"+{hp_increase} (Now {char['max_hp'] + hp_increase})")
        embed.add_field(name="✨ New Abilities", value="Check your class for new features!")
        
        await interaction.response.send_message(embed=embed)
    
    @character_group.command(name="rest", description="Take a rest to recover HP and mana")
    @app_commands.describe(rest_type="Type of rest to take")
    @app_commands.choices(rest_type=[
        app_commands.Choice(name="Short Rest (recover some HP)", value="short"),
        app_commands.Choice(name="Long Rest (full recovery)", value="long")
    ])
    async def rest(self, interaction: discord.Interaction, rest_type: str):
        """Rest to recover resources"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        if rest_type == "short":
            # Short rest: recover 25% HP
            hp_recovery = max(1, char['max_hp'] // 4)
            new_hp = min(char['max_hp'], char['hp'] + hp_recovery)
            mana_recovery = max(1, char['max_mana'] // 4)
            new_mana = min(char['max_mana'], char['mana'] + mana_recovery)
            
            await self.db.update_character(char['id'], hp=new_hp, mana=new_mana)
            
            embed = discord.Embed(
                title="☕ Short Rest",
                description=f"{char['name']} takes a brief rest...",
                color=discord.Color.green()
            )
            embed.add_field(name="❤️ HP Recovered", value=f"+{new_hp - char['hp']} ({new_hp}/{char['max_hp']})")
            if char['max_mana'] > 0:
                embed.add_field(name="✨ Mana Recovered", value=f"+{new_mana - char['mana']} ({new_mana}/{char['max_mana']})")
        
        else:  # Long rest
            await self.db.update_character(
                char['id'],
                hp=char['max_hp'],
                mana=char['max_mana']
            )
            
            embed = discord.Embed(
                title="🛏️ Long Rest",
                description=f"{char['name']} gets a full night's rest...",
                color=discord.Color.green()
            )
            embed.add_field(name="❤️ HP", value=f"Fully restored ({char['max_hp']}/{char['max_hp']})")
            if char['max_mana'] > 0:
                embed.add_field(name="✨ Mana", value=f"Fully restored ({char['max_mana']}/{char['max_mana']})")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Characters(bot))
