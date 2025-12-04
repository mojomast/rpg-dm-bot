"""
RPG DM Bot - Combat Cog
Handles combat mechanics, initiative, and combat actions
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import logging

logger = logging.getLogger('rpg.combat')


class CombatView(discord.ui.View):
    """Interactive combat action buttons"""
    
    def __init__(self, bot, encounter_id: int, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.encounter_id = encounter_id
        self.user_id = user_id
    
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
        
        await interaction.response.send_message(
            "🛡️ You take a defensive stance! (+2 AC until your next turn)",
            ephemeral=False
        )
    
    @discord.ui.button(label="Use Item", emoji="🧪", style=discord.ButtonStyle.secondary)
    async def item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "Item usage coming soon! Use `/inventory use` for now.",
            ephemeral=True
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
        
        # Calculate attack
        attack_bonus = (char['strength'] - 10) // 2  # Simplified
        attack_roll = random.randint(1, 20)
        total_attack = attack_roll + attack_bonus
        
        target_ac = 10  # Default AC
        
        is_crit = attack_roll == 20
        is_fumble = attack_roll == 1
        hit = (total_attack >= target_ac or is_crit) and not is_fumble
        
        # Build result message
        lines = []
        lines.append(f"⚔️ **{char['name']}** attacks!")
        lines.append(f"🎲 Attack Roll: {attack_roll} + {attack_bonus} = **{total_attack}** vs AC {target_ac}")
        
        if is_crit:
            lines.append("🎯 **CRITICAL HIT!**")
            damage = random.randint(2, 16)  # 2d8 for crit
        elif is_fumble:
            lines.append("💥 **CRITICAL MISS!**")
            damage = 0
        elif hit:
            lines.append("✅ **HIT!**")
            damage = random.randint(1, 8) + (char['strength'] - 10) // 2
        else:
            lines.append("❌ **MISS!**")
            damage = 0
        
        if hit and damage > 0:
            result = await self.bot.db.update_combatant_hp(target_id, -damage)
            lines.append(f"💥 Damage: **{damage}**")
            
            if result.get('is_dead'):
                lines.append(f"💀 **{result['name']} is defeated!**")
            else:
                lines.append(f"Enemy HP: {result['new_hp']}/{result['max_hp']}")
        
        await interaction.response.send_message("\n".join(lines))


class Combat(commands.Cog):
    """Combat system commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    combat_group = app_commands.Group(name="combat", description="Combat commands")
    
    @combat_group.command(name="start", description="Start a combat encounter")
    async def start_combat(self, interaction: discord.Interaction):
        """Start a new combat encounter"""
        # Check for existing combat
        existing = await self.db.get_active_combat(interaction.channel.id)
        if existing:
            await interaction.response.send_message(
                "❌ Combat is already active in this channel! Use `/combat end` to finish it.",
                ephemeral=True
            )
            return
        
        # Create combat
        guild_id = interaction.guild.id
        session = await self.db.get_active_session(guild_id)
        
        encounter_id = await self.db.create_combat(
            guild_id=guild_id,
            channel_id=interaction.channel.id,
            session_id=session['id'] if session else None
        )
        
        # Add the initiator's character
        char = await self.db.get_active_character(interaction.user.id, guild_id)
        if char:
            dex_mod = (char['dexterity'] - 10) // 2
            await self.db.add_combatant(
                encounter_id, 'character', char['id'], char['name'],
                char['hp'], char['max_hp'], dex_mod, is_player=True
            )
        
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
        combat = await self.db.get_active_combat(interaction.channel.id)
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
        
        dex_mod = (char['dexterity'] - 10) // 2
        await self.db.add_combatant(
            combat['id'], 'character', char['id'], char['name'],
            char['hp'], char['max_hp'], dex_mod, is_player=True
        )
        
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
        combat = await self.db.get_active_combat(interaction.channel.id)
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
            
            combatant_id = await self.db.add_combatant(
                combat['id'], 'enemy', 0, name, hp, hp, init_bonus, is_player=False
            )
            spawned.append(f"👹 {name} (HP: {hp})")
        
        embed = discord.Embed(
            title="👹 Enemies Appear!",
            description="\n".join(spawned),
            color=discord.Color.dark_red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @combat_group.command(name="initiative", description="Roll initiative for all combatants")
    async def roll_initiative(self, interaction: discord.Interaction):
        """Roll initiative and set turn order"""
        combat = await self.db.get_active_combat(interaction.channel.id)
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
    
    @combat_group.command(name="attack", description="Attack a target in combat")
    @app_commands.describe(target="Name of the target to attack")
    async def attack(self, interaction: discord.Interaction, target: str):
        """Attack a target"""
        combat = await self.db.get_active_combat(interaction.channel.id)
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
        
        # Roll attack
        str_mod = (char['strength'] - 10) // 2
        attack_roll = random.randint(1, 20)
        total = attack_roll + str_mod
        
        is_crit = attack_roll == 20
        is_fumble = attack_roll == 1
        target_ac = 10
        
        hit = (total >= target_ac or is_crit) and not is_fumble
        
        lines = []
        lines.append(f"⚔️ **{char['name']}** attacks **{target_combatant['name']}**!")
        lines.append(f"🎲 Roll: {attack_roll} + {str_mod} = **{total}** vs AC {target_ac}")
        
        if is_crit:
            damage = random.randint(2, 16) + str_mod  # 2d8 + mod
            lines.append(f"🎯 **CRITICAL HIT!** 💥 {damage} damage!")
        elif is_fumble:
            damage = 0
            lines.append("💥 **CRITICAL MISS!** Your attack goes wide!")
        elif hit:
            damage = random.randint(1, 8) + str_mod
            lines.append(f"✅ **HIT!** 💥 {damage} damage!")
        else:
            damage = 0
            lines.append("❌ **MISS!**")
        
        if hit and damage > 0:
            result = await self.db.update_combatant_hp(target_combatant['id'], -damage)
            
            if result.get('is_dead'):
                lines.append(f"💀 **{target_combatant['name']} is defeated!**")
            else:
                lines.append(f"Enemy HP: {result['new_hp']}/{result['max_hp']}")
        
        embed = discord.Embed(
            title="⚔️ Attack!",
            description="\n".join(lines),
            color=discord.Color.red() if hit else discord.Color.grey()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @combat_group.command(name="status", description="View current combat status")
    async def combat_status(self, interaction: discord.Interaction):
        """Show combat status"""
        combat = await self.db.get_active_combat(interaction.channel.id)
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
        combat = await self.db.get_active_combat(interaction.channel.id)
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
