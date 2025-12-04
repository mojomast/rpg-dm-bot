"""
RPG DM Bot - Dice Cog
Handles dice rolling commands
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import random
import re
from typing import Optional

logger = logging.getLogger('rpg.dice')

# Dice regex pattern: XdY+Z or XdY-Z
DICE_PATTERN = re.compile(r'^(\d+)?d(\d+)([+-]\d+)?$', re.IGNORECASE)

# Common dice presets
DICE_PRESETS = {
    "d4": (1, 4, 0),
    "d6": (1, 6, 0),
    "d8": (1, 8, 0),
    "d10": (1, 10, 0),
    "d12": (1, 12, 0),
    "d20": (1, 20, 0),
    "d100": (1, 100, 0),
    "2d6": (2, 6, 0),
    "4d6": (4, 6, 0),  # For stat rolling
}


class DiceView(discord.ui.View):
    """Quick dice rolling buttons"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.last_roll = None
    
    async def roll_dice(self, interaction: discord.Interaction, num: int, sides: int, mod: int = 0):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your dice panel!",
                ephemeral=True
            )
            return
        
        rolls = [random.randint(1, sides) for _ in range(num)]
        total = sum(rolls) + mod
        self.last_roll = (num, sides, mod, rolls, total)
        
        roll_str = ', '.join(str(r) for r in rolls)
        mod_str = f" + {mod}" if mod > 0 else f" - {abs(mod)}" if mod < 0 else ""
        
        # Check for crits on d20
        crit_msg = ""
        if sides == 20 and num == 1:
            if rolls[0] == 20:
                crit_msg = " 🎉 **NATURAL 20!**"
            elif rolls[0] == 1:
                crit_msg = " 💀 **NATURAL 1!**"
        
        embed = discord.Embed(
            title=f"🎲 {num}d{sides}{mod_str}",
            description=f"**Rolls:** [{roll_str}]{mod_str}\n**Total:** {total}{crit_msg}",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="d4", style=discord.ButtonStyle.secondary)
    async def roll_d4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.roll_dice(interaction, 1, 4)
    
    @discord.ui.button(label="d6", style=discord.ButtonStyle.secondary)
    async def roll_d6(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.roll_dice(interaction, 1, 6)
    
    @discord.ui.button(label="d8", style=discord.ButtonStyle.secondary)
    async def roll_d8(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.roll_dice(interaction, 1, 8)
    
    @discord.ui.button(label="d10", style=discord.ButtonStyle.secondary)
    async def roll_d10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.roll_dice(interaction, 1, 10)
    
    @discord.ui.button(label="d12", style=discord.ButtonStyle.secondary)
    async def roll_d12(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.roll_dice(interaction, 1, 12)
    
    @discord.ui.button(label="d20", style=discord.ButtonStyle.primary)
    async def roll_d20(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.roll_dice(interaction, 1, 20)
    
    @discord.ui.button(label="d100", style=discord.ButtonStyle.secondary)
    async def roll_d100(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.roll_dice(interaction, 1, 100)
    
    @discord.ui.button(label="2d6", style=discord.ButtonStyle.secondary)
    async def roll_2d6(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.roll_dice(interaction, 2, 6)
    
    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.success, emoji="🔄")
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.last_roll:
            num, sides, mod, _, _ = self.last_roll
            await self.roll_dice(interaction, num, sides, mod)
        else:
            await interaction.response.send_message(
                "No previous roll to repeat!",
                ephemeral=True
            )


def parse_dice_notation(notation: str) -> tuple:
    """Parse dice notation like 2d6+3, returns (num, sides, modifier)"""
    notation = notation.strip().lower()
    
    # Check presets first
    if notation in DICE_PRESETS:
        return DICE_PRESETS[notation]
    
    match = DICE_PATTERN.match(notation)
    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")
    
    num = int(match.group(1)) if match.group(1) else 1
    sides = int(match.group(2))
    mod = int(match.group(3)) if match.group(3) else 0
    
    # Sanity checks
    if num < 1 or num > 100:
        raise ValueError("Number of dice must be between 1 and 100")
    if sides < 2 or sides > 1000:
        raise ValueError("Dice sides must be between 2 and 1000")
    if abs(mod) > 1000:
        raise ValueError("Modifier must be between -1000 and 1000")
    
    return num, sides, mod


class Dice(commands.Cog):
    """Dice rolling commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="roll", description="Roll dice")
    @app_commands.describe(
        dice="Dice notation (e.g., d20, 2d6+3, 4d6)",
        hidden="Roll privately?"
    )
    async def roll(
        self,
        interaction: discord.Interaction,
        dice: str = "d20",
        hidden: bool = False
    ):
        """Roll dice using standard notation"""
        try:
            num, sides, mod = parse_dice_notation(dice)
        except ValueError as e:
            await interaction.response.send_message(
                f"❌ {str(e)}",
                ephemeral=True
            )
            return
        
        rolls = [random.randint(1, sides) for _ in range(num)]
        total = sum(rolls) + mod
        
        roll_str = ', '.join(str(r) for r in rolls)
        mod_str = f" + {mod}" if mod > 0 else f" - {abs(mod)}" if mod < 0 else ""
        
        # Check for crits on d20
        crit_msg = ""
        if sides == 20 and num == 1:
            if rolls[0] == 20:
                crit_msg = " 🎉 **NATURAL 20!**"
            elif rolls[0] == 1:
                crit_msg = " 💀 **NATURAL 1!**"
        
        embed = discord.Embed(
            title=f"🎲 {interaction.user.display_name} rolls {num}d{sides}{mod_str}",
            description=f"**Rolls:** [{roll_str}]{mod_str}\n**Total: {total}**{crit_msg}",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=hidden)
    
    @app_commands.command(name="dice", description="Open the dice panel")
    async def dice_panel(self, interaction: discord.Interaction):
        """Open interactive dice panel"""
        embed = discord.Embed(
            title="🎲 Dice Panel",
            description="Click a button to roll dice!",
            color=discord.Color.blue()
        )
        
        view = DiceView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="roll_stat", description="Roll for a stat (4d6 drop lowest)")
    async def roll_stat(self, interaction: discord.Interaction):
        """Roll 4d6 drop lowest for stat generation"""
        rolls = [random.randint(1, 6) for _ in range(4)]
        lowest = min(rolls)
        total = sum(rolls) - lowest
        
        # Format with strikethrough on dropped die
        formatted_rolls = []
        dropped = False
        for r in rolls:
            if r == lowest and not dropped:
                formatted_rolls.append(f"~~{r}~~")
                dropped = True
            else:
                formatted_rolls.append(str(r))
        
        embed = discord.Embed(
            title="🎲 Stat Roll (4d6 drop lowest)",
            description=f"**Rolls:** [{', '.join(formatted_rolls)}]\n**Total: {total}**",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="roll_stats", description="Roll a full set of stats")
    async def roll_stats(self, interaction: discord.Interaction):
        """Roll 6 stats using 4d6 drop lowest"""
        stats = []
        for _ in range(6):
            rolls = [random.randint(1, 6) for _ in range(4)]
            total = sum(rolls) - min(rolls)
            stats.append(total)
        
        stat_names = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        
        embed = discord.Embed(
            title="🎲 Stat Array (4d6 drop lowest × 6)",
            description="Assign these stats to your abilities:",
            color=discord.Color.gold()
        )
        
        for name, value in zip(stat_names, stats):
            mod = (value - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            embed.add_field(
                name=f"{name}",
                value=f"**{value}** ({mod_str})",
                inline=True
            )
        
        total = sum(stats)
        embed.set_footer(text=f"Total: {total} | Average: {total/6:.1f}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="roll_adv", description="Roll with advantage (2d20 keep highest)")
    async def roll_advantage(
        self,
        interaction: discord.Interaction,
        modifier: int = 0
    ):
        """Roll with advantage"""
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        best = max(roll1, roll2)
        total = best + modifier
        
        mod_str = f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}" if modifier < 0 else ""
        
        # Format rolls
        r1_str = f"**{roll1}**" if roll1 == best else f"~~{roll1}~~"
        r2_str = f"**{roll2}**" if roll2 == best else f"~~{roll2}~~"
        
        crit_msg = ""
        if best == 20:
            crit_msg = " 🎉 **NATURAL 20!**"
        elif best == 1:
            crit_msg = " 💀 **NATURAL 1!**"
        
        embed = discord.Embed(
            title="🎲 Roll with Advantage",
            description=f"**Rolls:** [{r1_str}, {r2_str}]{mod_str}\n**Total: {total}**{crit_msg}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="roll_dis", description="Roll with disadvantage (2d20 keep lowest)")
    async def roll_disadvantage(
        self,
        interaction: discord.Interaction,
        modifier: int = 0
    ):
        """Roll with disadvantage"""
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        worst = min(roll1, roll2)
        total = worst + modifier
        
        mod_str = f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}" if modifier < 0 else ""
        
        # Format rolls
        r1_str = f"**{roll1}**" if roll1 == worst else f"~~{roll1}~~"
        r2_str = f"**{roll2}**" if roll2 == worst else f"~~{roll2}~~"
        
        crit_msg = ""
        if worst == 20:
            crit_msg = " 🎉 **NATURAL 20!**"
        elif worst == 1:
            crit_msg = " 💀 **NATURAL 1!**"
        
        embed = discord.Embed(
            title="🎲 Roll with Disadvantage",
            description=f"**Rolls:** [{r1_str}, {r2_str}]{mod_str}\n**Total: {total}**{crit_msg}",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="flip", description="Flip a coin")
    async def flip_coin(self, interaction: discord.Interaction):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙"
        
        embed = discord.Embed(
            title=f"{emoji} Coin Flip",
            description=f"**{result}!**",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Dice(bot))
