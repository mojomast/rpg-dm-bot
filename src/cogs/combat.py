"""
RPG DM Bot - Combat Cog
Handles combat mechanics, initiative, and combat actions
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import logging

from src.cogs.inventory import get_item_data
from src.tools import DiceRoller, ToolExecutor
from src.utils import load_runtime_content

logger = logging.getLogger('rpg.combat')


async def resolve_attack(db, attacker_char: dict, target_combatant: dict) -> dict:
    """Resolve a simple weapon attack against a combatant."""
    str_mod = (attacker_char['strength'] - 10) // 2
    attack_roll = random.randint(1, 20)
    total = attack_roll + str_mod
    target_ac = target_combatant.get('armor_class') or target_combatant.get('combat_stats', {}).get('ac') or 10
    target_ac += sum(2 for effect in target_combatant.get('status_effects', []) if effect.get('effect') == 'defending')

    is_crit = attack_roll == 20
    is_fumble = attack_roll == 1
    hit = (total >= target_ac or is_crit) and not is_fumble

    damage = 0
    hp_result = None
    if is_crit:
        damage = random.randint(2, 16) + str_mod
    elif hit:
        damage = random.randint(1, 8) + str_mod

    if hit and damage > 0:
        hp_result = await db.update_combatant_hp(target_combatant['id'], -damage)

    return {
        'attack_roll': attack_roll,
        'attack_bonus': str_mod,
        'total': total,
        'target_ac': target_ac,
        'is_crit': is_crit,
        'is_fumble': is_fumble,
        'hit': hit,
        'damage': damage,
        'hp_result': hp_result,
    }


class CombatView(discord.ui.View):
    """Interactive combat action buttons"""
    
    def __init__(self, bot, encounter_id: int, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.encounter_id = encounter_id
        self.user_id = user_id

    async def _get_item_content(self, interaction: discord.Interaction, character: dict) -> dict:
        return await load_runtime_content(
            self.bot.db,
            'items.json',
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            channel_id=interaction.channel.id,
            character=character,
        )
    
    @discord.ui.button(label="Attack", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        
        # Show target selection
        combatants = await self.bot.db.get_combatants(self.encounter_id)
        enemies = [c for c in combatants if not c['is_player'] and c['current_hp'] > 0]
        
        if not enemies:
            await interaction.response.send_message("No enemies to attack!", ephemeral=True)
            return
        
        view = TargetSelectView(self.bot, self.encounter_id, enemies, "attack")
        await interaction.response.send_message("Select a target:", view=view, ephemeral=True)
    
    @discord.ui.button(label="Defend", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return

        char = await self.bot.db.get_active_character(interaction.user.id, interaction.guild.id)
        if not char:
            await interaction.response.send_message("No active character!", ephemeral=True)
            return

        combatants = await self.bot.db.get_combatants(self.encounter_id)
        participant = next(
            (c for c in combatants if c['participant_type'] == 'character' and c['participant_id'] == char['id']),
            None,
        )
        if not participant:
            await interaction.response.send_message("You are not in this combat!", ephemeral=True)
            return

        await self.bot.db.add_status_effect(participant['id'], 'defending', duration=1)
        
        await interaction.response.send_message(
            "🛡️ You take a defensive stance! (+2 AC until your next turn)",
            ephemeral=False
        )
    
    @discord.ui.button(label="Use Item", emoji="🧪", style=discord.ButtonStyle.secondary)
    async def item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return

        char = await self.bot.db.get_active_character(interaction.user.id, interaction.guild.id)
        if not char:
            await interaction.response.send_message("No active character!", ephemeral=True)
            return

        inventory = await self.bot.db.get_inventory(char['id'])
        item_content = await self._get_item_content(interaction, char)
        usable_items = []
        for item in inventory:
            if item['item_type'] != 'consumable':
                continue
            item_data = get_item_data(item_content, item['item_id'])
            effect = (item_data or {}).get('effect', {})
            if effect.get('type') in {'heal', 'restore_mana'}:
                usable_items.append(item)

        if not usable_items:
            await interaction.response.send_message("No usable combat items in your inventory.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Choose an item to use:",
            view=CombatItemView(self.bot, self.encounter_id, char, usable_items, item_content),
            ephemeral=True,
        )
    
    @discord.ui.button(label="Flee", emoji="🏃", style=discord.ButtonStyle.secondary)
    async def flee_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        
        # Roll DEX check to flee
        roll = random.randint(1, 20)
        success = roll >= 12
        
        if success:
            await interaction.response.send_message(
                f"🏃 You successfully flee from combat! (Rolled {roll})"
            )
        else:
            await interaction.response.send_message(
                f"❌ Failed to flee! (Rolled {roll}, needed 12+)\nThe enemies get an opportunity attack!"
            )


class TargetSelectView(discord.ui.View):
    """View for selecting combat targets"""
    
    def __init__(self, bot, encounter_id: int, targets: list, action: str):
        super().__init__(timeout=60)
        self.bot = bot
        self.encounter_id = encounter_id
        self.action = action
        
        # Add select menu for targets
        options = [
            discord.SelectOption(
                label=f"{t['name']} ({t['current_hp']}/{t['max_hp']} HP)",
                value=str(t['id'])
            )
            for t in targets[:25]  # Discord limit
        ]
        
        select = discord.ui.Select(
            placeholder="Choose your target...",
            options=options
        )
        select.callback = self.target_selected
        self.add_item(select)
    
    async def target_selected(self, interaction: discord.Interaction):
        target_id = int(interaction.data['values'][0])
        
        # Get attacker's character
        char = await self.bot.db.get_active_character(interaction.user.id, interaction.guild.id)
        if not char:
            await interaction.response.send_message("No active character!", ephemeral=True)
            return
        
        target_combatant = next((c for c in await self.bot.db.get_combatants(self.encounter_id) if c['id'] == target_id), None)
        if not target_combatant:
            await interaction.response.send_message("Target not found!", ephemeral=True)
            return

        attack = await resolve_attack(self.bot.db, char, target_combatant)
        
        # Build result message
        lines = []
        lines.append(f"⚔️ **{char['name']}** attacks **{target_combatant['name']}**!")
        lines.append(f"🎲 Attack Roll: {attack['attack_roll']} + {attack['attack_bonus']} = **{attack['total']}** vs AC {attack['target_ac']}")
        
        if attack['is_crit']:
            lines.append("🎯 **CRITICAL HIT!**")
        elif attack['is_fumble']:
            lines.append("💥 **CRITICAL MISS!**")
        elif attack['hit']:
            lines.append("✅ **HIT!**")
        else:
            lines.append("❌ **MISS!**")
        
        if attack['hit'] and attack['damage'] > 0:
            result = attack['hp_result'] or {}
            lines.append(f"💥 Damage: **{attack['damage']}**")
            
            if result.get('is_dead'):
                lines.append(f"💀 **{result['name']} is defeated!**")
            else:
                lines.append(f"Enemy HP: {result['new_hp']}/{result['max_hp']}")
        
        await interaction.response.send_message("\n".join(lines))


class CombatItemView(discord.ui.View):
    """View for selecting and using simple combat consumables."""

    def __init__(self, bot, encounter_id: int, character: dict, items: list, item_content: dict):
        super().__init__(timeout=60)
        self.bot = bot
        self.encounter_id = encounter_id
        self.character = character
        self.item_content = item_content

        options = [
            discord.SelectOption(
                label=f"{item['item_name']} x{item['quantity']}",
                value=str(item['id'])
            )
            for item in items[:25]
        ]

        select = discord.ui.Select(placeholder="Choose an item...", options=options)
        select.callback = self.item_selected
        self.add_item(select)

    async def item_selected(self, interaction: discord.Interaction):
        item_id = int(interaction.data['values'][0])
        inventory = await self.bot.db.get_inventory(self.character['id'])
        item = next((entry for entry in inventory if entry['id'] == item_id), None)
        if not item:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return

        item_data = get_item_data(self.item_content, item['item_id']) or {}
        effect = item_data.get('effect', {})
        effect_type = effect.get('type')
        lines = [f"🧪 **{self.character['name']}** uses **{item['item_name']}**!"]

        if effect_type == 'heal':
            roll = DiceRoller.roll(effect.get('value', '1'))
            if roll.get('error'):
                await interaction.response.send_message(f"Error: {roll['error']}", ephemeral=True)
                return

            combatants = await self.bot.db.get_combatants(self.encounter_id)
            participant = next(
                (c for c in combatants if c['participant_type'] == 'character' and c['participant_id'] == self.character['id']),
                None,
            )
            if not participant:
                await interaction.response.send_message("You are not in this combat!", ephemeral=True)
                return

            result = await self.bot.db.update_combatant_hp(participant['id'], roll['total'])
            await self.bot.db.update_character_hp(self.character['id'], roll['total'])
            lines.append(f"💚 Restored **{roll['total']}** HP")
            lines.append(f"HP: {result['new_hp']}/{result['max_hp']}")
        elif effect_type == 'restore_mana':
            new_mana = min(self.character['max_mana'], self.character['mana'] + int(effect.get('value', 0)))
            restored = new_mana - self.character['mana']
            await self.bot.db.update_character(self.character['id'], mana=new_mana)
            lines.append(f"✨ Restored **{restored}** mana")
            lines.append(f"Mana: {new_mana}/{self.character['max_mana']}")
        else:
            await interaction.response.send_message("That item cannot be used in combat yet.", ephemeral=True)
            return

        await self.bot.db.remove_item(item_id, 1)
        await interaction.response.send_message("\n".join(lines))


class Combat(commands.Cog):
    """Combat system commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.tool_executor = ToolExecutor(bot.db)
    
    @property
    def db(self):
        return self.bot.db
    
    combat_group = app_commands.Group(
        name="combat", 
        description="Combat commands",
        guild_only=True
    )
    
    @combat_group.command(name="start", description="Start a combat encounter")
    async def start_combat(self, interaction: discord.Interaction):
        """Start a new combat encounter"""
        # Check for existing combat
        existing = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
        if existing:
            await interaction.response.send_message(
                "❌ Combat is already active in this channel! Use `/combat end` to finish it.",
                ephemeral=True
            )
            return
        
        # Create combat
        guild_id = interaction.guild.id
        session = await self.db.get_session_by_channel(
            guild_id,
            interaction.channel.id,
            statuses=['active', 'paused', 'inactive'],
        )
        if not session:
            session = await self.db.get_user_active_session(guild_id, interaction.user.id)
        if not session:
            session = await self.db.get_active_session(guild_id)
        
        encounter_id = await self.db.create_combat(
            guild_id=guild_id,
            channel_id=interaction.channel.id,
            session_id=session['id'] if session else None
        )

        if session:
            participants = await self.db.get_session_participants(session['id'])
            for participant in participants:
                if participant.get('character_id'):
                    await self.tool_executor.add_character_combatant(encounter_id, participant['character_id'])
        else:
            char = await self.db.get_active_character(interaction.user.id, guild_id)
            if char:
                await self.tool_executor.add_character_combatant(encounter_id, char['id'])
        
        embed = discord.Embed(
            title="⚔️ Combat Started!",
            description="A battle begins!\n\n**DM:** Use `/combat spawn` to add enemies\n**Players:** Your characters will be added when you act",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📋 Commands",
            value="`/combat spawn` - Add enemies\n`/combat join` - Join the battle\n`/combat initiative` - Roll initiative\n`/combat status` - View combat state",
            inline=False
        )
        embed.set_footer(text=f"Encounter #{encounter_id}")
        
        await interaction.response.send_message(embed=embed)
    
    @combat_group.command(name="join", description="Join the current combat")
    async def join_combat(self, interaction: discord.Interaction):
        """Join active combat with your character"""
        combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
        if not combat:
            await interaction.response.send_message(
                "❌ No active combat in this channel!",
                ephemeral=True
            )
            return
        
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character! Use `/character create` first.",
                ephemeral=True
            )
            return
        
        # Check if already in combat
        combatants = await self.db.get_combatants(combat['id'])
        if any(c['participant_id'] == char['id'] and c['participant_type'] == 'character' for c in combatants):
            await interaction.response.send_message(
                "You're already in this combat!",
                ephemeral=True
            )
            return
        
        await self.tool_executor.add_character_combatant(combat['id'], char['id'])
        
        await interaction.response.send_message(
            f"⚔️ **{char['name']}** joins the battle!"
        )
    
    @combat_group.command(name="spawn", description="Spawn enemies (DM only)")
    @app_commands.describe(
        enemy_name="Name of the enemy",
        hp="Enemy's hit points",
        count="Number of enemies to spawn"
    )
    async def spawn_enemy(
        self,
        interaction: discord.Interaction,
        enemy_name: str,
        hp: int,
        count: int = 1
    ):
        """Spawn enemies in combat"""
        combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
        if not combat:
            await interaction.response.send_message(
                "❌ No active combat! Use `/combat start` first.",
                ephemeral=True
            )
            return
        
        spawned = []
        for i in range(count):
            name = f"{enemy_name}" if count == 1 else f"{enemy_name} {i+1}"
            init_bonus = random.randint(-1, 3)  # Random initiative bonus
            await self.tool_executor.add_enemy_combatant(
                combat['id'],
                name,
                hp,
                initiative_bonus=init_bonus,
            )
            spawned.append(f"👹 {name} (HP: {hp}, AC: 10)")
        
        embed = discord.Embed(
            title="👹 Enemies Appear!",
            description="\n".join(spawned),
            color=discord.Color.dark_red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @combat_group.command(name="initiative", description="Roll initiative for all combatants")
    async def roll_initiative(self, interaction: discord.Interaction):
        """Roll initiative and set turn order"""
        combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
        if not combat:
            await interaction.response.send_message(
                "❌ No active combat!",
                ephemeral=True
            )
            return
        
        combatants = await self.db.get_combatants(combat['id'])
        
        if not combatants:
            await interaction.response.send_message(
                "❌ No combatants in this encounter!",
                ephemeral=True
            )
            return
        
        # Roll initiative for each
        results = []
        for c in combatants:
            roll = random.randint(1, 20) + c['initiative']
            results.append({
                'name': c['name'],
                'roll': roll,
                'is_player': c['is_player'],
                'id': c['id']
            })
        
        # Sort by initiative (highest first)
        results.sort(key=lambda x: x['roll'], reverse=True)

        for result in results:
            await self.db.update_combatant_initiative(result['id'], result['roll'])
        await self.db.set_initiative_order(combat['id'], [result['id'] for result in results])
        await self.db.set_current_turn(combat['id'], 0)
        
        # Build display
        lines = ["**Initiative Order:**", ""]
        for i, r in enumerate(results):
            marker = "🎮" if r['is_player'] else "👹"
            arrow = "➡️ " if i == 0 else "   "
            lines.append(f"{arrow}{i+1}. {marker} **{r['name']}**: {r['roll']}")
        
        lines.append("")
        lines.append(f"🎯 **{results[0]['name']}'s turn!**")
        
        embed = discord.Embed(
            title="⚔️ Initiative Rolled!",
            description="\n".join(lines),
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)

    @combat_group.command(name="next", description="Advance to the next combat turn")
    async def next_turn(self, interaction: discord.Interaction):
        """Advance combat to the next turn."""
        combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
        if not combat:
            await interaction.response.send_message(
                "❌ No active combat!",
                ephemeral=True,
            )
            return

        result = await self.db.advance_combat_turn(combat['id'])
        if result.get('error'):
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return

        current = result['current_combatant']
        embed = discord.Embed(
            title="⏭️ Next Turn",
            description=(
                f"Round **{result['round']}**\n"
                f"It is now **{current['name']}**'s turn.\n"
                f"HP: {current['current_hp']}/{current['max_hp']}"
            ),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed)
    
    @combat_group.command(name="attack", description="Attack a target in combat")
    @app_commands.describe(target="Name of the target to attack")
    async def attack(self, interaction: discord.Interaction, target: str):
        """Attack a target"""
        combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
        if not combat:
            await interaction.response.send_message(
                "❌ No active combat!",
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
        
        # Find target
        combatants = await self.db.get_combatants(combat['id'])
        target_combatant = None
        for c in combatants:
            if target.lower() in c['name'].lower() and c['current_hp'] > 0:
                target_combatant = c
                break
        
        if not target_combatant:
            await interaction.response.send_message(
                f"❌ Target '{target}' not found or already defeated!",
                ephemeral=True
            )
            return
        
        attack = await resolve_attack(self.db, char, target_combatant)
        
        lines = []
        lines.append(f"⚔️ **{char['name']}** attacks **{target_combatant['name']}**!")
        lines.append(f"🎲 Roll: {attack['attack_roll']} + {attack['attack_bonus']} = **{attack['total']}** vs AC {attack['target_ac']}")
        
        if attack['is_crit']:
            lines.append(f"🎯 **CRITICAL HIT!** 💥 {attack['damage']} damage!")
        elif attack['is_fumble']:
            lines.append("💥 **CRITICAL MISS!** Your attack goes wide!")
        elif attack['hit']:
            lines.append(f"✅ **HIT!** 💥 {attack['damage']} damage!")
        else:
            lines.append("❌ **MISS!**")
        
        if attack['hit'] and attack['damage'] > 0:
            result = attack['hp_result'] or {}
            
            if result.get('is_dead'):
                lines.append(f"💀 **{target_combatant['name']} is defeated!**")
            else:
                lines.append(f"Enemy HP: {result['new_hp']}/{result['max_hp']}")
        
        embed = discord.Embed(
            title="⚔️ Attack!",
            description="\n".join(lines),
            color=discord.Color.red() if attack['hit'] else discord.Color.grey()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @combat_group.command(name="status", description="View current combat status")
    async def combat_status(self, interaction: discord.Interaction):
        """Show combat status"""
        combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
        if not combat:
            await interaction.response.send_message(
                "❌ No active combat in this channel!",
                ephemeral=True
            )
            return
        
        combatants = await self.db.get_combatants(combat['id'])
        
        if not combatants:
            await interaction.response.send_message(
                "No combatants in this encounter.",
                ephemeral=True
            )
            return
        
        lines = []
        for c in combatants:
            marker = "🎮" if c['is_player'] else "👹"
            dead = "💀 " if c['current_hp'] <= 0 else ""
            
            # HP bar
            hp_pct = c['current_hp'] / c['max_hp'] if c['max_hp'] > 0 else 0
            hp_bar = "█" * int(hp_pct * 10) + "░" * (10 - int(hp_pct * 10))
            
            # Status effects
            effects = c.get('status_effects', [])
            effect_str = " ".join([f"[{e['effect']}]" for e in effects]) if effects else ""
            
            lines.append(f"{dead}{marker} **{c['name']}**")
            lines.append(f"   {hp_bar} {c['current_hp']}/{c['max_hp']} HP {effect_str}")
        
        embed = discord.Embed(
            title=f"⚔️ Combat Status (Round {combat['round_number']})",
            description="\n".join(lines),
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @combat_group.command(name="end", description="End the current combat")
    async def end_combat(self, interaction: discord.Interaction):
        """End the combat encounter"""
        combat = await self.db.get_active_combat(interaction.guild.id, interaction.channel.id)
        if not combat:
            await interaction.response.send_message(
                "❌ No active combat to end!",
                ephemeral=True
            )
            return
        
        await self.db.end_combat(combat['id'])
        
        embed = discord.Embed(
            title="⚔️ Combat Ended",
            description="The battle has concluded!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Combat(bot))
