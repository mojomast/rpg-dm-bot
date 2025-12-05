"""
Skills & Skill Trees Cog
Handles skill learning, skill tree progression, and active skill usage
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List, Dict, Any
import json
import os
import random

# Load skills data
SKILLS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'game_data', 'skills.json')
SKILLS_DATA = {}

def load_skills():
    global SKILLS_DATA
    try:
        with open(SKILLS_FILE, 'r', encoding='utf-8') as f:
            SKILLS_DATA = json.load(f)
    except FileNotFoundError:
        SKILLS_DATA = {"skill_trees": {}, "skills": {}, "passive_abilities": {}, "status_effects": {}}

load_skills()


# ============================================================================
# SKILL TREE VIEW
# ============================================================================

class SkillTreeView(discord.ui.View):
    """View for browsing skill trees"""
    
    def __init__(self, cog, character: Dict, char_class: str):
        super().__init__(timeout=180)
        self.cog = cog
        self.character = character
        self.char_class = char_class.lower()
        self.current_branch = None
        
        # Get branches for this class
        tree = SKILLS_DATA.get('skill_trees', {}).get(self.char_class, {})
        self.branches = tree.get('branches', [])
        
        if self.branches:
            self.add_item(BranchSelectDropdown(cog, character, self.char_class, self.branches))
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, row=2)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the skill tree view"""
        embed = await self.cog.create_skill_tree_embed(self.character, self.char_class)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📊 My Skills", style=discord.ButtonStyle.primary, row=2)
    async def my_skills(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show learned skills"""
        skills = await self.cog.bot.db.get_character_skills(self.character['id'])
        
        if not skills:
            await interaction.response.send_message(
                "📭 You haven't learned any skills yet! Use `/skill learn` to unlock skills.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"⚔️ {self.character['name']}'s Skills",
            color=discord.Color.gold()
        )
        
        # Group by branch
        by_branch = {}
        for skill in skills:
            branch = skill['skill_branch']
            if branch not in by_branch:
                by_branch[branch] = []
            by_branch[branch].append(skill)
        
        for branch, branch_skills in by_branch.items():
            skill_lines = []
            for s in sorted(branch_skills, key=lambda x: x['skill_tier']):
                skill_data = SKILLS_DATA.get('skills', {}).get(s['skill_id'], {})
                icon = skill_data.get('icon', '⚡')
                passive = " (Passive)" if s['is_passive'] else ""
                
                if s['max_uses']:
                    uses = f" [{s['uses_remaining']}/{s['max_uses']}]"
                else:
                    uses = ""
                
                cooldown = f" 🕐{s['cooldown_remaining']}" if s['cooldown_remaining'] > 0 else ""
                skill_lines.append(f"{icon} **{s['skill_name']}** T{s['skill_tier']}{passive}{uses}{cooldown}")
            
            embed.add_field(
                name=f"📂 {branch.replace('_', ' ').title()}",
                value="\n".join(skill_lines) or "None",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class BranchSelectDropdown(discord.ui.Select):
    """Dropdown for selecting a skill tree branch"""
    
    def __init__(self, cog, character: Dict, char_class: str, branches: List[Dict]):
        self.cog = cog
        self.character = character
        self.char_class = char_class
        self.branch_map = {b['id']: b for b in branches}
        
        options = []
        for branch in branches:
            options.append(discord.SelectOption(
                label=branch['name'],
                value=branch['id'],
                description=branch.get('description', '')[:100],
                emoji=branch.get('icon', '📚')
            ))
        
        super().__init__(
            placeholder="📂 Choose a skill branch...",
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        branch_id = self.values[0]
        branch = self.branch_map.get(branch_id)
        
        if not branch:
            await interaction.response.send_message("❌ Branch not found!", ephemeral=True)
            return
        
        # Show branch details with skills
        embed = await self.cog.create_branch_embed(
            self.character, self.char_class, branch
        )
        
        view = BranchSkillsView(self.cog, self.character, self.char_class, branch)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class BranchSkillsView(discord.ui.View):
    """View for skills within a branch"""
    
    def __init__(self, cog, character: Dict, char_class: str, branch: Dict):
        super().__init__(timeout=120)
        self.cog = cog
        self.character = character
        self.char_class = char_class
        self.branch = branch
        
        # Get skills in this branch
        branch_skills = []
        for skill_id in branch.get('skills', []):
            skill = SKILLS_DATA.get('skills', {}).get(skill_id)
            if skill:
                branch_skills.append({'id': skill_id, **skill})
        
        if branch_skills:
            self.add_item(SkillLearnDropdown(cog, character, branch_skills))


class SkillLearnDropdown(discord.ui.Select):
    """Dropdown for learning a skill"""
    
    def __init__(self, cog, character: Dict, skills: List[Dict]):
        self.cog = cog
        self.character = character
        self.skill_map = {s['id']: s for s in skills}
        
        options = []
        for skill in skills[:25]:
            tier_text = f"Tier {skill.get('tier', 1)}"
            cost = skill.get('skill_point_cost', 1)
            
            options.append(discord.SelectOption(
                label=skill['name'][:50],
                value=skill['id'],
                description=f"{tier_text} | Cost: {cost} points",
                emoji=skill.get('icon', '⚡')
            ))
        
        super().__init__(
            placeholder="🎓 Choose a skill to learn...",
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        skill_id = self.values[0]
        skill = self.skill_map.get(skill_id)
        
        if not skill:
            await interaction.response.send_message("❌ Skill not found!", ephemeral=True)
            return
        
        # Show skill details with learn button
        embed = discord.Embed(
            title=f"{skill.get('icon', '⚡')} {skill['name']}",
            description=skill.get('description', 'No description'),
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Tier", value=str(skill.get('tier', 1)), inline=True)
        embed.add_field(name="Cost", value=f"{skill.get('skill_point_cost', 1)} points", inline=True)
        embed.add_field(name="Type", value="Passive" if skill.get('is_passive') else "Active", inline=True)
        
        if skill.get('cooldown'):
            embed.add_field(name="Cooldown", value=f"{skill['cooldown']} turns", inline=True)
        
        if skill.get('uses_per_rest'):
            embed.add_field(
                name="Uses", 
                value=f"{skill['uses_per_rest']}/{skill.get('recharge', 'long_rest').replace('_', ' ')}", 
                inline=True
            )
        
        if skill.get('effects'):
            effect_text = []
            for effect in skill['effects']:
                effect_text.append(f"• {effect.get('type', 'effect')}: {effect.get('value', 'N/A')}")
            embed.add_field(name="Effects", value="\n".join(effect_text), inline=False)
        
        if skill.get('prerequisites'):
            prereq_text = ", ".join(skill['prerequisites'])
            embed.add_field(name="Prerequisites", value=prereq_text, inline=False)
        
        view = LearnSkillConfirmView(self.cog, self.character, skill_id, skill)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class LearnSkillConfirmView(discord.ui.View):
    """Confirmation view for learning a skill"""
    
    def __init__(self, cog, character: Dict, skill_id: str, skill: Dict):
        super().__init__(timeout=60)
        self.cog = cog
        self.character = character
        self.skill_id = skill_id
        self.skill = skill
    
    @discord.ui.button(label="✅ Learn Skill", style=discord.ButtonStyle.success)
    async def learn(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = await self.cog.learn_skill(
            interaction, self.character, self.skill_id, self.skill
        )
        if result:
            self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Cancelled.", ephemeral=True)
        self.stop()


# ============================================================================
# SKILL USAGE VIEW
# ============================================================================

class UseSkillView(discord.ui.View):
    """View for using active skills"""
    
    def __init__(self, cog, character: Dict, skills: List[Dict], target: str = None):
        super().__init__(timeout=120)
        self.cog = cog
        self.character = character
        self.skills = skills
        self.target = target
        
        # Filter to active skills only
        active_skills = [s for s in skills if not s.get('is_passive')]
        
        if active_skills:
            self.add_item(SkillUseDropdown(cog, character, active_skills, target))


class SkillUseDropdown(discord.ui.Select):
    """Dropdown for selecting a skill to use"""
    
    def __init__(self, cog, character: Dict, skills: List[Dict], target: str = None):
        self.cog = cog
        self.character = character
        self.target = target
        self.skill_map = {s['skill_id']: s for s in skills}
        
        options = []
        for skill in skills[:25]:
            skill_data = SKILLS_DATA.get('skills', {}).get(skill['skill_id'], {})
            
            # Show availability status
            available = True
            status = ""
            
            if skill.get('cooldown_remaining', 0) > 0:
                available = False
                status = f" [CD: {skill['cooldown_remaining']}]"
            elif skill.get('max_uses') and skill.get('uses_remaining', 0) <= 0:
                available = False
                status = " [No uses]"
            
            emoji = skill_data.get('icon', '⚡') if available else "❌"
            
            options.append(discord.SelectOption(
                label=f"{skill['skill_name']}{status}"[:50],
                value=skill['skill_id'],
                description=skill_data.get('description', '')[:100] if available else "Not available",
                emoji=emoji
            ))
        
        super().__init__(
            placeholder="⚡ Choose a skill to use...",
            options=options if options else [discord.SelectOption(label="No skills", value="none")]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("You don't have any active skills!", ephemeral=True)
            return
        
        skill_id = self.values[0]
        skill_db = self.skill_map.get(skill_id)
        skill_data = SKILLS_DATA.get('skills', {}).get(skill_id, {})
        
        if not skill_data:
            await interaction.response.send_message("❌ Skill data not found!", ephemeral=True)
            return
        
        # Execute the skill
        await self.cog.execute_skill(
            interaction, self.character, skill_id, skill_data, skill_db, self.target
        )


# ============================================================================
# TARGET SELECTION VIEW
# ============================================================================

class TargetSelectView(discord.ui.View):
    """View for selecting a target for skills"""
    
    def __init__(self, cog, character: Dict, skill_id: str, skill_data: Dict, 
                 skill_db: Dict, targets: List[Dict]):
        super().__init__(timeout=60)
        self.cog = cog
        self.character = character
        self.skill_id = skill_id
        self.skill_data = skill_data
        self.skill_db = skill_db
        
        if targets:
            self.add_item(TargetSelectDropdown(cog, character, skill_id, skill_data, skill_db, targets))
    
    @discord.ui.button(label="🎯 Self", style=discord.ButtonStyle.primary, row=1)
    async def target_self(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.execute_skill(
            interaction, self.character, self.skill_id, self.skill_data, 
            self.skill_db, self.character['name']
        )
        self.stop()


class TargetSelectDropdown(discord.ui.Select):
    """Dropdown for selecting a target"""
    
    def __init__(self, cog, character: Dict, skill_id: str, skill_data: Dict, 
                 skill_db: Dict, targets: List[Dict]):
        self.cog = cog
        self.character = character
        self.skill_id = skill_id
        self.skill_data = skill_data
        self.skill_db = skill_db
        self.target_map = {str(t.get('id', t.get('name'))): t for t in targets}
        
        options = []
        for target in targets[:25]:
            name = target.get('name', 'Unknown')
            hp_text = ""
            if 'hp' in target and 'max_hp' in target:
                hp_text = f" ({target['hp']}/{target['max_hp']} HP)"
            
            options.append(discord.SelectOption(
                label=f"{name}{hp_text}"[:50],
                value=str(target.get('id', name)),
                emoji="🎯"
            ))
        
        super().__init__(
            placeholder="🎯 Choose a target...",
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        target_key = self.values[0]
        target = self.target_map.get(target_key, {})
        target_name = target.get('name', target_key)
        
        await self.cog.execute_skill(
            interaction, self.character, self.skill_id, self.skill_data, 
            self.skill_db, target_name
        )
        self.view.stop()


# ============================================================================
# SKILLS COG
# ============================================================================

class Skills(commands.Cog):
    """Skills and skill tree management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def create_skill_tree_embed(self, character: Dict, char_class: str) -> discord.Embed:
        """Create an embed showing the skill tree overview"""
        tree = SKILLS_DATA.get('skill_trees', {}).get(char_class.lower(), {})
        
        embed = discord.Embed(
            title=f"🌳 {tree.get('name', char_class.title())} Skill Tree",
            description=tree.get('description', 'Choose a branch to explore'),
            color=discord.Color.green()
        )
        
        # Get skill points
        skill_points = await self.bot.db.get_skill_points(character['id'])
        embed.add_field(
            name="🎯 Skill Points",
            value=f"Available: **{skill_points['available']}** | Spent: {skill_points['spent']}",
            inline=False
        )
        
        # Show branches
        for branch in tree.get('branches', []):
            branch_skills = []
            for skill_id in branch.get('skills', [])[:5]:
                skill = SKILLS_DATA.get('skills', {}).get(skill_id, {})
                has_skill = await self.bot.db.has_skill(character['id'], skill_id)
                icon = "✅" if has_skill else skill.get('icon', '⚡')
                branch_skills.append(f"{icon} {skill.get('name', skill_id)}")
            
            embed.add_field(
                name=f"{branch.get('icon', '📂')} {branch['name']}",
                value="\n".join(branch_skills) if branch_skills else "No skills",
                inline=True
            )
        
        embed.set_footer(text="Select a branch to view details and learn skills")
        return embed
    
    async def create_branch_embed(self, character: Dict, char_class: str, branch: Dict) -> discord.Embed:
        """Create an embed showing a skill branch"""
        embed = discord.Embed(
            title=f"{branch.get('icon', '📂')} {branch['name']}",
            description=branch.get('description', 'Explore this skill branch'),
            color=discord.Color.blue()
        )
        
        # Group skills by tier
        by_tier = {}
        for skill_id in branch.get('skills', []):
            skill = SKILLS_DATA.get('skills', {}).get(skill_id)
            if skill:
                tier = skill.get('tier', 1)
                if tier not in by_tier:
                    by_tier[tier] = []
                by_tier[tier].append({'id': skill_id, **skill})
        
        # Show skills by tier
        for tier in sorted(by_tier.keys()):
            skills_text = []
            for skill in by_tier[tier]:
                has_skill = await self.bot.db.has_skill(character['id'], skill['id'])
                status = "✅" if has_skill else "⬜"
                passive = " (P)" if skill.get('is_passive') else ""
                cost = skill.get('skill_point_cost', 1)
                skills_text.append(f"{status} {skill.get('icon', '⚡')} **{skill['name']}**{passive} - {cost} pts")
            
            embed.add_field(
                name=f"🔷 Tier {tier}",
                value="\n".join(skills_text) or "None",
                inline=False
            )
        
        return embed
    
    async def learn_skill(self, interaction: discord.Interaction, character: Dict, 
                          skill_id: str, skill: Dict) -> bool:
        """Learn a skill for a character"""
        # Check if already learned
        if await self.bot.db.has_skill(character['id'], skill_id):
            await interaction.response.send_message(
                f"❌ You already know **{skill['name']}**!",
                ephemeral=True
            )
            return False
        
        # Check skill points
        cost = skill.get('skill_point_cost', 1)
        skill_points = await self.bot.db.get_skill_points(character['id'])
        
        if skill_points['available'] < cost:
            await interaction.response.send_message(
                f"❌ Not enough skill points! Need {cost}, have {skill_points['available']}.",
                ephemeral=True
            )
            return False
        
        # Check prerequisites
        prerequisites = skill.get('prerequisites', [])
        for prereq_id in prerequisites:
            if not await self.bot.db.has_skill(character['id'], prereq_id):
                prereq_skill = SKILLS_DATA.get('skills', {}).get(prereq_id, {})
                prereq_name = prereq_skill.get('name', prereq_id)
                await interaction.response.send_message(
                    f"❌ You need to learn **{prereq_name}** first!",
                    ephemeral=True
                )
                return False
        
        # Spend points and learn skill
        await self.bot.db.spend_skill_points(character['id'], cost)
        
        # Determine branch from skill data or default
        branch = skill.get('branch', 'general')
        
        await self.bot.db.learn_skill(
            character_id=character['id'],
            skill_id=skill_id,
            skill_name=skill['name'],
            skill_branch=branch,
            skill_tier=skill.get('tier', 1),
            is_passive=skill.get('is_passive', False),
            max_uses=skill.get('uses_per_rest'),
            recharge=skill.get('recharge', 'long_rest')
        )
        
        embed = discord.Embed(
            title="🎓 Skill Learned!",
            description=f"You have learned **{skill['name']}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="Description", value=skill.get('description', 'N/A'), inline=False)
        embed.add_field(name="Points Spent", value=str(cost), inline=True)
        embed.add_field(name="Points Remaining", value=str(skill_points['available'] - cost), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return True
    
    async def execute_skill(self, interaction: discord.Interaction, character: Dict,
                           skill_id: str, skill_data: Dict, skill_db: Dict, 
                           target: str = None) -> bool:
        """Execute a skill"""
        # Check cooldown
        if skill_db.get('cooldown_remaining', 0) > 0:
            await interaction.response.send_message(
                f"❌ **{skill_data['name']}** is on cooldown for {skill_db['cooldown_remaining']} more turns!",
                ephemeral=True
            )
            return False
        
        # Check uses
        if skill_db.get('max_uses') and skill_db.get('uses_remaining', 0) <= 0:
            await interaction.response.send_message(
                f"❌ No uses remaining for **{skill_data['name']}**! Take a rest to recover.",
                ephemeral=True
            )
            return False
        
        # Use the skill
        success = await self.bot.db.use_skill(character['id'], skill_id)
        if not success:
            await interaction.response.send_message(
                "❌ Failed to use skill!",
                ephemeral=True
            )
            return False
        
        # Set cooldown if applicable
        cooldown = skill_data.get('cooldown', 0)
        if cooldown > 0:
            await self.bot.db.set_skill_cooldown(character['id'], skill_id, cooldown)
        
        # Build result embed
        embed = discord.Embed(
            title=f"{skill_data.get('icon', '⚡')} {skill_data['name']}",
            color=discord.Color.gold()
        )
        
        embed.description = f"**{character['name']}** uses **{skill_data['name']}**"
        if target:
            embed.description += f" on **{target}**"
        embed.description += "!"
        
        # Process effects
        effects_text = []
        for effect in skill_data.get('effects', []):
            effect_type = effect.get('type', '')
            value = effect.get('value', 0)
            
            if effect_type == 'damage':
                # Roll damage
                damage = self.roll_damage(value)
                damage_type = effect.get('damage_type', 'physical')
                effects_text.append(f"💥 Deals **{damage}** {damage_type} damage!")
            
            elif effect_type == 'heal':
                healing = self.roll_damage(value)
                effects_text.append(f"💚 Heals for **{healing}** HP!")
                # Apply healing to self
                await self.bot.db.update_character_hp(character['id'], healing)
            
            elif effect_type == 'buff':
                duration = effect.get('duration', 3)
                stat = effect.get('stat', 'attack')
                effects_text.append(f"⬆️ +{value} to {stat} for {duration} turns")
                # Apply status effect
                await self.bot.db.apply_status_effect(
                    character['id'], f"buff_{stat}", f"{stat.title()} Buff",
                    'buff', duration=duration,
                    properties={'stat': stat, 'value': value}
                )
            
            elif effect_type == 'debuff':
                duration = effect.get('duration', 3)
                stat = effect.get('stat', 'defense')
                effects_text.append(f"⬇️ -{value} to target's {stat} for {duration} turns")
            
            elif effect_type == 'apply_status':
                status_id = effect.get('status')
                duration = effect.get('duration', 3)
                status_data = SKILLS_DATA.get('status_effects', {}).get(status_id, {})
                status_name = status_data.get('name', status_id)
                effects_text.append(f"🎭 Applies **{status_name}** for {duration} turns")
        
        if effects_text:
            embed.add_field(name="Effects", value="\n".join(effects_text), inline=False)
        
        # Show cooldown/uses info
        footer_parts = []
        if cooldown > 0:
            footer_parts.append(f"Cooldown: {cooldown} turns")
        if skill_db.get('max_uses'):
            remaining = max(0, skill_db.get('uses_remaining', 1) - 1)
            footer_parts.append(f"Uses: {remaining}/{skill_db['max_uses']}")
        
        if footer_parts:
            embed.set_footer(text=" | ".join(footer_parts))
        
        await interaction.response.send_message(embed=embed)
        return True
    
    def roll_damage(self, dice_string: str) -> int:
        """Roll dice and return total (e.g., '2d6+3')"""
        try:
            if isinstance(dice_string, int):
                return dice_string
            
            total = 0
            parts = dice_string.replace('-', '+-').split('+')
            
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                
                if 'd' in part.lower():
                    num, sides = part.lower().split('d')
                    num = int(num) if num else 1
                    sides = int(sides)
                    for _ in range(abs(num)):
                        roll = random.randint(1, sides)
                        total += roll if num > 0 else -roll
                else:
                    total += int(part)
            
            return max(0, total)
        except:
            return 0
    
    # ========================================================================
    # COMMANDS
    # ========================================================================
    
    @app_commands.command(name="skills", description="View your skill tree")
    async def view_skills(self, interaction: discord.Interaction):
        """View and manage your skills"""
        character = await self.bot.db.get_active_character(
            interaction.user.id, interaction.guild_id
        )
        
        if not character:
            await interaction.response.send_message(
                "❌ You need an active character! Use `/character create` first.",
                ephemeral=True
            )
            return
        
        char_class = character['class'].lower()
        
        if char_class not in SKILLS_DATA.get('skill_trees', {}):
            await interaction.response.send_message(
                f"❌ No skill tree found for class **{character['class']}**!",
                ephemeral=True
            )
            return
        
        embed = await self.create_skill_tree_embed(character, char_class)
        view = SkillTreeView(self, character, char_class)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="useskill", description="Use an active skill")
    @app_commands.describe(target="Optional target for the skill")
    async def use_skill(self, interaction: discord.Interaction, target: str = None):
        """Use one of your learned skills"""
        character = await self.bot.db.get_active_character(
            interaction.user.id, interaction.guild_id
        )
        
        if not character:
            await interaction.response.send_message(
                "❌ You need an active character! Use `/character create` first.",
                ephemeral=True
            )
            return
        
        # Get learned skills
        skills = await self.bot.db.get_character_skills(character['id'])
        
        if not skills:
            await interaction.response.send_message(
                "📭 You haven't learned any skills yet! Use `/skills` to view your skill tree.",
                ephemeral=True
            )
            return
        
        # Filter active skills
        active_skills = [s for s in skills if not s.get('is_passive')]
        
        if not active_skills:
            await interaction.response.send_message(
                "📭 You don't have any active skills! All your skills are passive.",
                ephemeral=True
            )
            return
        
        view = UseSkillView(self, character, active_skills, target)
        
        embed = discord.Embed(
            title="⚡ Use Skill",
            description="Select a skill to use",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="skillinfo", description="View details about a skill")
    @app_commands.describe(skill_name="Name of the skill to look up")
    async def skill_info(self, interaction: discord.Interaction, skill_name: str):
        """Look up information about a skill"""
        # Search for skill
        skill_id = None
        skill_data = None
        
        for sid, sdata in SKILLS_DATA.get('skills', {}).items():
            if sdata.get('name', '').lower() == skill_name.lower():
                skill_id = sid
                skill_data = sdata
                break
        
        if not skill_data:
            # Try partial match
            for sid, sdata in SKILLS_DATA.get('skills', {}).items():
                if skill_name.lower() in sdata.get('name', '').lower():
                    skill_id = sid
                    skill_data = sdata
                    break
        
        if not skill_data:
            await interaction.response.send_message(
                f"❌ Skill **{skill_name}** not found!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"{skill_data.get('icon', '⚡')} {skill_data['name']}",
            description=skill_data.get('description', 'No description'),
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Tier", value=str(skill_data.get('tier', 1)), inline=True)
        embed.add_field(name="Cost", value=f"{skill_data.get('skill_point_cost', 1)} points", inline=True)
        embed.add_field(name="Type", value="Passive" if skill_data.get('is_passive') else "Active", inline=True)
        
        if skill_data.get('cooldown'):
            embed.add_field(name="Cooldown", value=f"{skill_data['cooldown']} turns", inline=True)
        
        if skill_data.get('uses_per_rest'):
            recharge = skill_data.get('recharge', 'long_rest').replace('_', ' ')
            embed.add_field(name="Uses", value=f"{skill_data['uses_per_rest']} per {recharge}", inline=True)
        
        if skill_data.get('effects'):
            effect_lines = []
            for effect in skill_data['effects']:
                etype = effect.get('type', 'effect')
                value = effect.get('value', 'N/A')
                effect_lines.append(f"• **{etype}**: {value}")
            embed.add_field(name="Effects", value="\n".join(effect_lines), inline=False)
        
        if skill_data.get('prerequisites'):
            prereqs = []
            for prereq_id in skill_data['prerequisites']:
                prereq = SKILLS_DATA.get('skills', {}).get(prereq_id, {})
                prereqs.append(prereq.get('name', prereq_id))
            embed.add_field(name="Prerequisites", value=", ".join(prereqs), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @skill_info.autocomplete('skill_name')
    async def skill_name_autocomplete(self, interaction: discord.Interaction, 
                                      current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for skill names"""
        choices = []
        for skill_id, skill_data in SKILLS_DATA.get('skills', {}).items():
            name = skill_data.get('name', skill_id)
            if current.lower() in name.lower():
                choices.append(app_commands.Choice(name=name[:100], value=name[:100]))
        return choices[:25]
    
    @app_commands.command(name="addskillpoints", description="[DM] Add skill points to a character")
    @app_commands.describe(
        member="The player to give skill points to",
        points="Number of skill points to add"
    )
    async def add_skill_points(self, interaction: discord.Interaction, 
                               member: discord.Member, points: int):
        """DM command to add skill points"""
        # Check if user is DM (simple check - could be enhanced)
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Only DMs can add skill points!",
                ephemeral=True
            )
            return
        
        character = await self.bot.db.get_active_character(member.id, interaction.guild_id)
        
        if not character:
            await interaction.response.send_message(
                f"❌ {member.display_name} doesn't have an active character!",
                ephemeral=True
            )
            return
        
        await self.bot.db.add_skill_points(character['id'], points)
        
        new_points = await self.bot.db.get_skill_points(character['id'])
        
        embed = discord.Embed(
            title="🎯 Skill Points Added",
            description=f"**{character['name']}** received **{points}** skill points!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Total Points", value=str(new_points['total']), inline=True)
        embed.add_field(name="Available", value=str(new_points['available']), inline=True)
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Skills(bot))
