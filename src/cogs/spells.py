"""
Spells & Abilities Cog
Handles spell casting, spell management, and class abilities
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List, Dict, Any
import json
import os
import random

# Load spells data
SPELLS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'game_data', 'spells.json')
SPELLS_DATA = {}

def load_spells():
    global SPELLS_DATA
    try:
        with open(SPELLS_FILE, 'r', encoding='utf-8') as f:
            SPELLS_DATA = json.load(f)
    except FileNotFoundError:
        SPELLS_DATA = {"spells": {}, "class_spell_lists": {}}

load_spells()


class SpellSelectView(discord.ui.View):
    """View for selecting a spell to cast"""
    
    def __init__(self, cog, character: Dict, spells: List[Dict], target: str = None):
        super().__init__(timeout=120)
        self.cog = cog
        self.character = character
        self.spells = spells
        self.target = target
        
        if spells:
            self.add_item(SpellSelectDropdown(cog, character, spells, target))


class SpellSelectDropdown(discord.ui.Select):
    """Dropdown for spell selection"""
    
    def __init__(self, cog, character: Dict, spells: List[Dict], target: str = None):
        self.cog = cog
        self.character = character
        self.target = target
        self.spell_map = {s['spell_id']: s for s in spells}
        
        options = []
        for spell in spells[:25]:  # Discord limit
            spell_data = SPELLS_DATA.get('spells', {}).get(spell['spell_id'], {})
            level_text = "Cantrip" if spell['is_cantrip'] else f"Level {spell['spell_level']}"
            emoji = "✨" if spell['is_cantrip'] else "🔮"
            
            options.append(discord.SelectOption(
                label=spell['spell_name'][:50],
                value=spell['spell_id'],
                description=f"{level_text} | {spell_data.get('school', 'Unknown').title()}",
                emoji=emoji
            ))
        
        super().__init__(
            placeholder="🎯 Choose a spell to cast...",
            options=options if options else [discord.SelectOption(label="No spells", value="none")]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("You don't know any spells!", ephemeral=True)
            return
        
        spell_id = self.values[0]
        spell_db = self.spell_map.get(spell_id)
        spell_data = SPELLS_DATA.get('spells', {}).get(spell_id, {})
        
        if not spell_data:
            await interaction.response.send_message("❌ Spell data not found!", ephemeral=True)
            return
        
        # Check if cantrip or needs slot
        if spell_db['is_cantrip']:
            # Cantrips don't use slots
            result = await self.cog.execute_spell(
                interaction, self.character, spell_id, spell_data, self.target
            )
        else:
            # Show slot selection
            view = SlotSelectView(
                self.cog, self.character, spell_id, spell_data, 
                spell_db['spell_level'], self.target
            )
            
            slots = await self.cog.bot.db.get_spell_slots(self.character['id'])
            if not slots:
                await interaction.response.send_message(
                    "❌ You have no spell slots! Take a rest to recover.",
                    ephemeral=True
                )
                return
            
            slot_text = "\n".join([
                f"**Level {lvl}:** {data['remaining']}/{data['total']}"
                for lvl, data in sorted(slots.items())
            ])
            
            embed = discord.Embed(
                title=f"🔮 Cast {spell_data['name']}",
                description=f"Choose a spell slot level (minimum: {spell_db['spell_level']})",
                color=discord.Color.purple()
            )
            embed.add_field(name="Available Slots", value=slot_text or "None", inline=False)
            
            if spell_data.get('upcast'):
                embed.add_field(
                    name="📈 Upcasting",
                    value=spell_data['upcast'],
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class SlotSelectView(discord.ui.View):
    """View for selecting spell slot level"""
    
    def __init__(self, cog, character: Dict, spell_id: str, spell_data: Dict, 
                 min_level: int, target: str = None):
        super().__init__(timeout=60)
        self.cog = cog
        self.character = character
        self.spell_id = spell_id
        self.spell_data = spell_data
        self.min_level = min_level
        self.target = target
        
        # Add buttons for valid slot levels
        for level in range(min_level, 6):  # Levels 1-5
            btn = discord.ui.Button(
                label=f"Level {level}",
                style=discord.ButtonStyle.primary if level == min_level else discord.ButtonStyle.secondary,
                custom_id=f"slot_{level}"
            )
            btn.callback = self.make_callback(level)
            self.add_item(btn)
    
    def make_callback(self, level: int):
        async def callback(interaction: discord.Interaction):
            # Check if slot available
            slots = await self.cog.bot.db.get_spell_slots(self.character['id'])
            if level not in slots or slots[level]['remaining'] <= 0:
                await interaction.response.send_message(
                    f"❌ No level {level} spell slots remaining!",
                    ephemeral=True
                )
                return
            
            # Use the slot
            await self.cog.bot.db.use_spell_slot(self.character['id'], level)
            
            # Calculate upcast bonus
            upcast_levels = level - self.min_level
            
            # Execute the spell
            await self.cog.execute_spell(
                interaction, self.character, self.spell_id, 
                self.spell_data, self.target, upcast_levels
            )
            self.stop()
        return callback


class LearnSpellView(discord.ui.View):
    """View for learning new spells"""
    
    def __init__(self, cog, character: Dict, available_spells: List[Dict]):
        super().__init__(timeout=120)
        self.cog = cog
        self.character = character
        
        if available_spells:
            self.add_item(LearnSpellDropdown(cog, character, available_spells))


class LearnSpellDropdown(discord.ui.Select):
    """Dropdown for learning a spell"""
    
    def __init__(self, cog, character: Dict, available_spells: List[Dict]):
        self.cog = cog
        self.character = character
        self.spell_map = {s['id']: s for s in available_spells}
        
        options = []
        for spell in available_spells[:25]:
            level_text = "Cantrip" if spell['level'] == 0 else f"Level {spell['level']}"
            options.append(discord.SelectOption(
                label=spell['name'][:50],
                value=spell['id'],
                description=f"{level_text} | {spell.get('school', 'Unknown').title()}",
                emoji="✨" if spell['level'] == 0 else "📖"
            ))
        
        super().__init__(
            placeholder="📚 Select a spell to learn...",
            options=options if options else [discord.SelectOption(label="No spells available", value="none")]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("No spells available to learn!", ephemeral=True)
            return
        
        spell_id = self.values[0]
        spell = self.spell_map.get(spell_id)
        
        if not spell:
            await interaction.response.send_message("❌ Spell not found!", ephemeral=True)
            return
        
        # Learn the spell
        result = await self.cog.bot.db.learn_spell(
            character_id=self.character['id'],
            spell_id=spell_id,
            spell_name=spell['name'],
            spell_level=spell['level'],
            is_cantrip=(spell['level'] == 0),
            source='class'
        )
        
        if result == -1:
            await interaction.response.send_message(
                f"You already know **{spell['name']}**!",
                ephemeral=True
            )
        else:
            embed = discord.Embed(
                title="📖 Spell Learned!",
                description=f"**{self.character['name']}** has learned **{spell['name']}**!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Spell Info",
                value=f"**Level:** {'Cantrip' if spell['level'] == 0 else spell['level']}\n"
                      f"**School:** {spell.get('school', 'Unknown').title()}\n"
                      f"**Casting Time:** {spell.get('casting_time', 'Unknown')}",
                inline=False
            )
            if spell.get('description'):
                embed.add_field(
                    name="Description",
                    value=spell['description'][:500],
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
        
        self.view.stop()


class Spells(commands.Cog):
    """Spell casting and management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    spell_group = app_commands.Group(
        name="spell",
        description="Spell casting and management",
        guild_only=True
    )
    
    @spell_group.command(name="cast", description="Cast a spell")
    @app_commands.describe(
        spell_name="Name of the spell to cast (optional - opens selection)",
        target="Target of the spell (creature or location)"
    )
    async def cast_spell(
        self,
        interaction: discord.Interaction,
        spell_name: Optional[str] = None,
        target: Optional[str] = None
    ):
        """Cast a spell from your known spells"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first! Use `/character create`",
                ephemeral=True
            )
            return
        
        # Get character's spells
        spells = await self.db.get_character_spells(char['id'], prepared_only=True)
        
        if not spells:
            await interaction.response.send_message(
                f"❌ **{char['name']}** doesn't know any spells!\n"
                "Use `/spell learn` to learn spells or check if your class can cast.",
                ephemeral=True
            )
            return
        
        if spell_name:
            # Find specific spell
            spell_lower = spell_name.lower()
            matching = [s for s in spells if spell_lower in s['spell_name'].lower()]
            
            if not matching:
                await interaction.response.send_message(
                    f"❌ You don't know a spell called '{spell_name}'!",
                    ephemeral=True
                )
                return
            
            spell = matching[0]
            spell_data = SPELLS_DATA.get('spells', {}).get(spell['spell_id'], {})
            
            if spell['is_cantrip']:
                await self.execute_spell(interaction, char, spell['spell_id'], spell_data, target)
            else:
                # Need to select slot
                view = SlotSelectView(self, char, spell['spell_id'], spell_data, spell['spell_level'], target)
                slots = await self.db.get_spell_slots(char['id'])
                
                slot_text = "\n".join([
                    f"**Level {lvl}:** {data['remaining']}/{data['total']}"
                    for lvl, data in sorted(slots.items())
                ])
                
                embed = discord.Embed(
                    title=f"🔮 Cast {spell_data.get('name', spell['spell_name'])}",
                    description=f"Choose a spell slot (minimum level {spell['spell_level']})",
                    color=discord.Color.purple()
                )
                embed.add_field(name="Available Slots", value=slot_text or "None", inline=False)
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            # Show spell selection
            view = SpellSelectView(self, char, spells, target)
            
            embed = discord.Embed(
                title=f"🔮 {char['name']}'s Spellbook",
                description="Select a spell to cast:",
                color=discord.Color.purple()
            )
            
            # Group by level
            cantrips = [s for s in spells if s['is_cantrip']]
            leveled = [s for s in spells if not s['is_cantrip']]
            
            if cantrips:
                cantrip_text = ", ".join([s['spell_name'] for s in cantrips[:10]])
                embed.add_field(name="✨ Cantrips", value=cantrip_text, inline=False)
            
            if leveled:
                leveled_text = ", ".join([f"{s['spell_name']} (Lv{s['spell_level']})" for s in leveled[:10]])
                embed.add_field(name="📖 Spells", value=leveled_text, inline=False)
            
            # Show spell slots
            slots = await self.db.get_spell_slots(char['id'])
            if slots:
                slot_text = " | ".join([f"Lv{lvl}: {data['remaining']}/{data['total']}" for lvl, data in sorted(slots.items())])
                embed.add_field(name="💫 Spell Slots", value=slot_text, inline=False)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def execute_spell(
        self,
        interaction: discord.Interaction,
        character: Dict,
        spell_id: str,
        spell_data: Dict,
        target: str = None,
        upcast_levels: int = 0
    ):
        """Execute a spell and show the result"""
        # Build the result
        spell_name = spell_data.get('name', spell_id)
        
        embed = discord.Embed(
            title=f"✨ {character['name']} casts {spell_name}!",
            color=discord.Color.purple()
        )
        
        if target:
            embed.description = f"*Targeting: {target}*"
        
        # Handle damage spells
        if spell_data.get('damage'):
            damage_dice = spell_data['damage']
            
            # Apply scaling for cantrips
            if spell_data.get('scaling') and upcast_levels == 0:
                char_level = character.get('level', 1)
                scaling = spell_data['scaling']
                for level_threshold, scaled_damage in sorted(scaling.items(), key=lambda x: int(x[0]), reverse=True):
                    if char_level >= int(level_threshold):
                        damage_dice = scaled_damage
                        break
            
            # Apply upcast bonus
            if upcast_levels > 0 and spell_data.get('upcast') and 'd' in spell_data.get('upcast', ''):
                # Simple upcast: add dice
                if '+1d' in spell_data['upcast']:
                    import re
                    match = re.search(r'\+1d(\d+)', spell_data['upcast'])
                    if match:
                        extra_die = f"d{match.group(1)}"
                        damage_dice = f"{damage_dice}+{upcast_levels}{extra_die}"
            
            # Roll damage
            from src.cogs.dice import DiceRoller
            roller = DiceRoller()
            result = roller.roll(damage_dice)
            
            damage_type = spell_data.get('damage_type', 'magical')
            
            embed.add_field(
                name="💥 Damage",
                value=f"**{result['total']}** {damage_type} damage\n"
                      f"🎲 {damage_dice} → {result['rolls']}",
                inline=True
            )
            
            if spell_data.get('save'):
                embed.add_field(
                    name="🛡️ Saving Throw",
                    value=f"{spell_data['save'].upper()} save for half damage",
                    inline=True
                )
        
        # Handle healing spells
        elif spell_data.get('healing'):
            healing_dice = spell_data['healing'].replace(' + spellcasting modifier', '')
            
            # Apply upcast
            if upcast_levels > 0 and spell_data.get('upcast') and '+1d' in spell_data.get('upcast', ''):
                import re
                match = re.search(r'\+1d(\d+)', spell_data['upcast'])
                if match:
                    extra_die = f"d{match.group(1)}"
                    healing_dice = f"{healing_dice}+{upcast_levels}{extra_die}"
            
            from src.cogs.dice import DiceRoller
            roller = DiceRoller()
            
            # Add wisdom modifier for divine casters, int for arcane
            char_class = character.get('char_class', '').lower()
            if char_class in ['cleric', 'paladin', 'ranger', 'druid']:
                mod = (character.get('wisdom', 10) - 10) // 2
            else:
                mod = (character.get('charisma', 10) - 10) // 2
            
            if mod > 0:
                healing_dice = f"{healing_dice}+{mod}"
            
            result = roller.roll(healing_dice)
            
            embed.add_field(
                name="💚 Healing",
                value=f"**{result['total']}** HP restored\n"
                      f"🎲 {healing_dice} → {result['rolls']}",
                inline=True
            )
        
        # Handle effect-only spells
        elif spell_data.get('effect'):
            embed.add_field(
                name="✨ Effect",
                value=spell_data['effect'],
                inline=False
            )
        
        # Add description
        if spell_data.get('description'):
            embed.add_field(
                name="📜 Description",
                value=spell_data['description'][:500],
                inline=False
            )
        
        # Show casting info
        casting_info = []
        if spell_data.get('casting_time'):
            casting_info.append(f"⏱️ {spell_data['casting_time']}")
        if spell_data.get('range'):
            casting_info.append(f"📏 {spell_data['range']}")
        if spell_data.get('duration') and spell_data['duration'] != 'Instantaneous':
            casting_info.append(f"⏳ {spell_data['duration']}")
        
        if casting_info:
            embed.set_footer(text=" | ".join(casting_info))
        
        await interaction.response.send_message(embed=embed)
    
    @spell_group.command(name="list", description="View your known spells")
    async def list_spells(self, interaction: discord.Interaction):
        """List all spells known by your character"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first!",
                ephemeral=True
            )
            return
        
        spells = await self.db.get_character_spells(char['id'])
        
        embed = discord.Embed(
            title=f"📖 {char['name']}'s Spellbook",
            description=f"Level {char['level']} {char['char_class']}",
            color=discord.Color.blue()
        )
        
        if not spells:
            embed.description += "\n\n*No spells known. Use `/spell learn` to learn spells!*"
        else:
            # Group by level
            cantrips = [s for s in spells if s['is_cantrip']]
            by_level = {}
            for s in spells:
                if not s['is_cantrip']:
                    lvl = s['spell_level']
                    if lvl not in by_level:
                        by_level[lvl] = []
                    by_level[lvl].append(s)
            
            if cantrips:
                cantrip_list = "\n".join([
                    f"• {s['spell_name']}" for s in cantrips
                ])
                embed.add_field(name="✨ Cantrips", value=cantrip_list, inline=False)
            
            for lvl in sorted(by_level.keys()):
                spell_list = "\n".join([
                    f"• {s['spell_name']}" + (" ✅" if s['is_prepared'] else " ⬜")
                    for s in by_level[lvl]
                ])
                embed.add_field(name=f"📖 Level {lvl}", value=spell_list, inline=True)
        
        # Show spell slots
        slots = await self.db.get_spell_slots(char['id'])
        if slots:
            slot_text = "\n".join([
                f"**Level {lvl}:** {data['remaining']}/{data['total']} slots"
                for lvl, data in sorted(slots.items())
            ])
            embed.add_field(name="💫 Spell Slots", value=slot_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @spell_group.command(name="learn", description="Learn a new spell")
    async def learn_spell(self, interaction: discord.Interaction):
        """Learn a new spell from your class spell list"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first!",
                ephemeral=True
            )
            return
        
        char_class = char['char_class'].lower()
        level = char['level']
        
        # Check if class can cast spells
        class_spells = SPELLS_DATA.get('class_spell_lists', {}).get(char_class)
        
        if not class_spells:
            await interaction.response.send_message(
                f"❌ {char['char_class']}s cannot cast spells!",
                ephemeral=True
            )
            return
        
        # Get currently known spells
        known = await self.db.get_character_spells(char['id'])
        known_ids = {s['spell_id'] for s in known}
        
        # Get available spells based on level
        available = []
        all_spells = SPELLS_DATA.get('spells', {})
        
        # Add cantrips
        for spell_id in class_spells.get('cantrips', []):
            if spell_id not in known_ids and spell_id in all_spells:
                spell = all_spells[spell_id].copy()
                spell['id'] = spell_id
                available.append(spell)
        
        # Add leveled spells (up to half character level rounded up)
        max_spell_level = min(5, (level + 1) // 2)
        for spell_lvl in range(1, max_spell_level + 1):
            for spell_id in class_spells.get(str(spell_lvl), []):
                if spell_id not in known_ids and spell_id in all_spells:
                    spell = all_spells[spell_id].copy()
                    spell['id'] = spell_id
                    available.append(spell)
        
        if not available:
            await interaction.response.send_message(
                f"**{char['name']}** has learned all available spells for their level!",
                ephemeral=True
            )
            return
        
        view = LearnSpellView(self, char, available)
        
        embed = discord.Embed(
            title=f"📚 Learn a New Spell",
            description=f"**{char['name']}** - Level {level} {char['char_class']}\n\n"
                       f"Select a spell to add to your spellbook:",
            color=discord.Color.blue()
        )
        
        # Show some available spells
        cantrips = [s for s in available if s['level'] == 0]
        leveled = [s for s in available if s['level'] > 0]
        
        if cantrips:
            embed.add_field(
                name="✨ Available Cantrips",
                value=", ".join([s['name'] for s in cantrips[:8]]),
                inline=False
            )
        
        if leveled:
            embed.add_field(
                name="📖 Available Spells",
                value=", ".join([f"{s['name']} (Lv{s['level']})" for s in leveled[:8]]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @spell_group.command(name="info", description="Get detailed info about a spell")
    @app_commands.describe(spell_name="Name of the spell to look up")
    async def spell_info(self, interaction: discord.Interaction, spell_name: str):
        """Get detailed information about a spell"""
        spell_lower = spell_name.lower().replace(' ', '_')
        
        # Search for spell
        all_spells = SPELLS_DATA.get('spells', {})
        matching = None
        
        for spell_id, spell in all_spells.items():
            if spell_lower in spell_id or spell_lower in spell.get('name', '').lower():
                matching = spell
                matching['id'] = spell_id
                break
        
        if not matching:
            await interaction.response.send_message(
                f"❌ Spell '{spell_name}' not found!",
                ephemeral=True
            )
            return
        
        level_text = "Cantrip" if matching['level'] == 0 else f"Level {matching['level']}"
        
        embed = discord.Embed(
            title=f"📖 {matching['name']}",
            description=f"*{matching.get('school', 'Unknown').title()} {level_text}*",
            color=discord.Color.purple()
        )
        
        # Casting details
        embed.add_field(
            name="⏱️ Casting Time",
            value=matching.get('casting_time', 'Unknown'),
            inline=True
        )
        embed.add_field(
            name="📏 Range",
            value=matching.get('range', 'Unknown'),
            inline=True
        )
        embed.add_field(
            name="⏳ Duration",
            value=matching.get('duration', 'Unknown'),
            inline=True
        )
        
        # Components
        components = matching.get('components', [])
        comp_text = ", ".join(components) if components else "None"
        embed.add_field(name="🧪 Components", value=comp_text, inline=True)
        
        # Damage/Healing
        if matching.get('damage'):
            embed.add_field(
                name="💥 Damage",
                value=f"{matching['damage']} {matching.get('damage_type', '')}",
                inline=True
            )
        
        if matching.get('healing'):
            embed.add_field(
                name="💚 Healing",
                value=matching['healing'],
                inline=True
            )
        
        # Effect
        if matching.get('effect'):
            embed.add_field(
                name="✨ Effect",
                value=matching['effect'][:200],
                inline=False
            )
        
        # Description
        if matching.get('description'):
            embed.add_field(
                name="📜 Description",
                value=matching['description'][:500],
                inline=False
            )
        
        # Upcast
        if matching.get('upcast'):
            embed.add_field(
                name="📈 At Higher Levels",
                value=matching['upcast'],
                inline=False
            )
        
        # Classes
        classes = matching.get('classes', [])
        if classes:
            embed.add_field(
                name="📚 Classes",
                value=", ".join([c.title() for c in classes]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @spell_group.command(name="slots", description="View and manage your spell slots")
    async def spell_slots(self, interaction: discord.Interaction):
        """View current spell slots"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first!",
                ephemeral=True
            )
            return
        
        slots = await self.db.get_spell_slots(char['id'])
        
        embed = discord.Embed(
            title=f"💫 {char['name']}'s Spell Slots",
            description=f"Level {char['level']} {char['char_class']}",
            color=discord.Color.blue()
        )
        
        if not slots:
            embed.description += "\n\n*No spell slots available.*\n*Your class may not have spellcasting, or you need to level up.*"
        else:
            for lvl, data in sorted(slots.items()):
                filled = "🔮" * data['remaining'] + "⬜" * (data['total'] - data['remaining'])
                embed.add_field(
                    name=f"Level {lvl}",
                    value=f"{filled}\n{data['remaining']}/{data['total']} remaining",
                    inline=True
                )
        
        embed.set_footer(text="Spell slots recover after a long rest. Use /rest to recover.")
        
        await interaction.response.send_message(embed=embed)
    
    @spell_group.command(name="prepare", description="Prepare spells for the day")
    async def prepare_spells(self, interaction: discord.Interaction):
        """Manage spell preparation"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first!",
                ephemeral=True
            )
            return
        
        spells = await self.db.get_character_spells(char['id'])
        
        # Filter to non-cantrip spells (cantrips are always prepared)
        preparable = [s for s in spells if not s['is_cantrip']]
        
        if not preparable:
            await interaction.response.send_message(
                "❌ No spells available to prepare! Learn some spells first with `/spell learn`.",
                ephemeral=True
            )
            return
        
        view = PrepareSpellsView(self, char, preparable)
        
        # Calculate prep limit (usually wisdom/int mod + level)
        char_class = char['char_class'].lower()
        if char_class in ['cleric', 'druid', 'paladin']:
            mod = (char.get('wisdom', 10) - 10) // 2
        else:
            mod = (char.get('intelligence', 10) - 10) // 2
        prep_limit = max(1, char['level'] + mod)
        
        prepared_count = len([s for s in preparable if s['is_prepared']])
        
        embed = discord.Embed(
            title=f"📋 Prepare Spells - {char['name']}",
            description=f"Prepared: **{prepared_count}/{prep_limit}**\n\n"
                       "Select spells to prepare or unprepare:",
            color=discord.Color.blue()
        )
        
        # Show prepared spells
        prepared = [s for s in preparable if s['is_prepared']]
        unprepared = [s for s in preparable if not s['is_prepared']]
        
        if prepared:
            prepared_text = "\n".join([f"✅ {s['spell_name']} (Lv{s['spell_level']})" for s in prepared[:10]])
            embed.add_field(name="Prepared", value=prepared_text, inline=True)
        
        if unprepared:
            unprepared_text = "\n".join([f"⬜ {s['spell_name']} (Lv{s['spell_level']})" for s in unprepared[:10]])
            embed.add_field(name="Not Prepared", value=unprepared_text, inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @spell_group.command(name="quickcast", description="Quick cast a spell by name")
    @app_commands.describe(
        spell_name="Name of the spell",
        slot_level="Spell slot level to use (auto-selects minimum if not provided)",
        target="Target of the spell"
    )
    async def quickcast(
        self,
        interaction: discord.Interaction,
        spell_name: str,
        slot_level: Optional[int] = None,
        target: Optional[str] = None
    ):
        """Quick cast a spell without menus"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first!",
                ephemeral=True
            )
            return
        
        spells = await self.db.get_character_spells(char['id'], prepared_only=True)
        
        # Find matching spell
        spell_lower = spell_name.lower()
        spell_db = None
        for s in spells:
            if spell_lower in s['spell_name'].lower():
                spell_db = s
                break
        
        if not spell_db:
            await interaction.response.send_message(
                f"❌ You don't have a prepared spell matching '{spell_name}'!",
                ephemeral=True
            )
            return
        
        spell_data = SPELLS_DATA.get('spells', {}).get(spell_db['spell_id'], {})
        
        # Cantrips don't use slots
        if spell_db['is_cantrip']:
            await self.execute_spell(interaction, char, spell_db['spell_id'], spell_data, target)
            return
        
        # Use provided slot level or minimum
        use_level = slot_level if slot_level else spell_db['spell_level']
        
        if use_level < spell_db['spell_level']:
            await interaction.response.send_message(
                f"❌ {spell_data.get('name', spell_db['spell_name'])} requires at least level {spell_db['spell_level']} slot!",
                ephemeral=True
            )
            return
        
        # Check slot availability
        slots = await self.db.get_spell_slots(char['id'])
        if use_level not in slots or slots[use_level]['remaining'] <= 0:
            await interaction.response.send_message(
                f"❌ No level {use_level} spell slots remaining!",
                ephemeral=True
            )
            return
        
        # Use the slot
        await self.db.use_spell_slot(char['id'], use_level)
        
        # Calculate upcast bonus
        upcast_levels = use_level - spell_db['spell_level']
        
        # Execute
        await self.execute_spell(interaction, char, spell_db['spell_id'], spell_data, target, upcast_levels)
    
    @quickcast.autocomplete('spell_name')
    async def quickcast_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for spell names"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        if not char:
            return []
        
        spells = await self.db.get_character_spells(char['id'], prepared_only=True)
        choices = []
        
        for spell in spells:
            if current.lower() in spell['spell_name'].lower():
                choices.append(app_commands.Choice(
                    name=spell['spell_name'][:100],
                    value=spell['spell_name'][:100]
                ))
        
        return choices[:25]


class PrepareSpellsView(discord.ui.View):
    """View for preparing/unpreparing spells"""
    
    def __init__(self, cog, character: Dict, spells: List[Dict]):
        super().__init__(timeout=120)
        self.cog = cog
        self.character = character
        self.spells = spells
        
        # Add dropdown for toggling preparation
        self.add_item(PrepareSpellDropdown(cog, character, spells))


class PrepareSpellDropdown(discord.ui.Select):
    """Dropdown to toggle spell preparation"""
    
    def __init__(self, cog, character: Dict, spells: List[Dict]):
        self.cog = cog
        self.character = character
        self.spell_map = {s['spell_id']: s for s in spells}
        
        options = []
        for spell in spells[:25]:
            status = "✅ " if spell['is_prepared'] else "⬜ "
            options.append(discord.SelectOption(
                label=f"{status}{spell['spell_name']}",
                value=spell['spell_id'],
                description=f"Level {spell['spell_level']} | {'Prepared' if spell['is_prepared'] else 'Not prepared'}",
                emoji="🔮" if spell['is_prepared'] else "📖"
            ))
        
        super().__init__(
            placeholder="🔮 Toggle spell preparation...",
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        spell_id = self.values[0]
        spell = self.spell_map.get(spell_id)
        
        if not spell:
            await interaction.response.send_message("Spell not found!", ephemeral=True)
            return
        
        # Toggle preparation
        new_state = not spell['is_prepared']
        await self.cog.db.set_spell_prepared(self.character['id'], spell_id, new_state)
        
        # Update local state
        spell['is_prepared'] = new_state
        
        action = "prepared" if new_state else "unprepared"
        await interaction.response.send_message(
            f"{'✅' if new_state else '⬜'} **{spell['spell_name']}** has been {action}!",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Spells(bot))
