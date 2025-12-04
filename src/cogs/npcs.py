"""
RPG DM Bot - NPCs Cog
Handles NPC creation, interaction, and dialogue
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
from typing import Optional

logger = logging.getLogger('rpg.npcs')

# NPC templates for quick creation
NPC_TEMPLATES = {
    "merchant": {
        "personality": "A shrewd but fair trader who always has interesting wares.",
        "default_dialogue": "Welcome, traveler! Care to see my wares?",
        "traits": ["greedy", "knowledgeable", "cautious"]
    },
    "guard": {
        "personality": "A stern protector of the realm, loyal to their duty.",
        "default_dialogue": "Halt! State your business.",
        "traits": ["dutiful", "suspicious", "honorable"]
    },
    "innkeeper": {
        "personality": "A jovial host who loves to hear stories from travelers.",
        "default_dialogue": "Come in, come in! Rest your weary bones!",
        "traits": ["friendly", "gossipy", "generous"]
    },
    "wizard": {
        "personality": "A mysterious mage with knowledge of arcane secrets.",
        "default_dialogue": "Ah, a seeker of knowledge... or perhaps power?",
        "traits": ["mysterious", "wise", "eccentric"]
    },
    "villain": {
        "personality": "A cunning adversary with their own dark agenda.",
        "default_dialogue": "So, you've finally arrived... I've been expecting you.",
        "traits": ["cunning", "cruel", "ambitious"]
    },
    "peasant": {
        "personality": "A humble villager trying to survive in difficult times.",
        "default_dialogue": "Please, kind stranger, can you help us?",
        "traits": ["humble", "fearful", "hardworking"]
    }
}


class CreateNPCModal(discord.ui.Modal, title="Create New NPC"):
    """Modal for creating a new NPC"""
    
    npc_name = discord.ui.TextInput(
        label="NPC Name",
        placeholder="Grimwald the Merchant",
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Description",
        style=discord.TextStyle.paragraph,
        placeholder="A tall, bearded man with keen eyes and a worn leather apron...",
        max_length=500
    )
    
    personality = discord.ui.TextInput(
        label="Personality & Behavior",
        style=discord.TextStyle.paragraph,
        placeholder="How does this NPC act? What are their motivations?",
        max_length=500
    )
    
    location = discord.ui.TextInput(
        label="Location",
        placeholder="The Rusty Sword Tavern",
        max_length=100,
        required=False
    )
    
    def __init__(self, bot, npc_type: Optional[str] = None):
        super().__init__()
        self.bot = bot
        self.npc_type = npc_type
        
        # Pre-fill with template if provided
        if npc_type and npc_type in NPC_TEMPLATES:
            template = NPC_TEMPLATES[npc_type]
            self.personality.default = template['personality']
    
    async def on_submit(self, interaction: discord.Interaction):
        npc_id = await self.bot.db.create_npc(
            guild_id=interaction.guild.id,
            name=str(self.npc_name),
            description=str(self.description),
            personality=str(self.personality),
            location=str(self.location) if self.location.value else "Unknown",
            npc_type=self.npc_type or "custom",
            created_by=interaction.user.id
        )
        
        embed = discord.Embed(
            title=f"✅ NPC Created: {self.npc_name}",
            description=str(self.description),
            color=discord.Color.green()
        )
        embed.add_field(name="Location", value=str(self.location) or "Unknown", inline=True)
        embed.add_field(name="Type", value=self.npc_type or "Custom", inline=True)
        embed.add_field(name="NPC ID", value=str(npc_id), inline=True)
        embed.add_field(name="Personality", value=str(self.personality)[:200], inline=False)
        
        await interaction.response.send_message(embed=embed)


class NPCDialogueView(discord.ui.View):
    """View for NPC dialogue interaction"""
    
    def __init__(self, bot, npc: dict, channel_id: int):
        super().__init__(timeout=600)
        self.bot = bot
        self.npc = npc
        self.channel_id = channel_id
        self.conversation_history = []
    
    @discord.ui.button(label="Talk", style=discord.ButtonStyle.primary, emoji="💬")
    async def talk(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open dialogue modal"""
        modal = NPCTalkModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Examine", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def examine(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Get detailed description"""
        embed = discord.Embed(
            title=f"🔍 Examining: {self.npc['name']}",
            description=self.npc['description'],
            color=discord.Color.blue()
        )
        embed.add_field(name="Location", value=self.npc['location'], inline=True)
        embed.add_field(name="Type", value=self.npc['npc_type'].title(), inline=True)
        
        if self.npc.get('personality'):
            embed.add_field(name="Demeanor", value=self.npc['personality'][:200], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Trade", style=discord.ButtonStyle.success, emoji="💰")
    async def trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open trade menu if NPC is merchant"""
        if self.npc['npc_type'] != 'merchant':
            await interaction.response.send_message(
                f"*{self.npc['name']} looks at you confused.* \"I'm not a merchant, friend.\"",
                ephemeral=True
            )
            return
        
        # Could open shop view here
        await interaction.response.send_message(
            f"*{self.npc['name']} opens their pack.* \"Let's see what I have for you...\"",
            ephemeral=True
        )
    
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, emoji="👋")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        """End conversation"""
        await interaction.response.edit_message(
            content=f"*You step away from {self.npc['name']}.*",
            embed=None,
            view=None
        )
        self.stop()


class NPCTalkModal(discord.ui.Modal, title="Say something to the NPC"):
    """Modal for NPC dialogue input"""
    
    message = discord.ui.TextInput(
        label="What do you say?",
        style=discord.TextStyle.paragraph,
        placeholder="Type your message to the NPC...",
        max_length=500
    )
    
    def __init__(self, parent_view: NPCDialogueView):
        super().__init__()
        self.parent = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        user_message = str(self.message)
        npc = self.parent.npc
        
        # Add to history
        self.parent.conversation_history.append({
            "role": "user",
            "content": f"[{interaction.user.display_name}]: {user_message}"
        })
        
        # Generate NPC response using LLM
        try:
            npc_context = f"""You are roleplaying as {npc['name']}, an NPC in a fantasy RPG.
Description: {npc['description']}
Personality: {npc['personality']}
Location: {npc['location']}
Type: {npc['npc_type']}

Stay in character. Respond as this NPC would. Keep responses under 200 words.
Only respond with the NPC's dialogue and actions (in *asterisks* for actions)."""
            
            messages = [
                {"role": "system", "content": npc_context},
                *self.parent.conversation_history
            ]
            
            response = await self.parent.bot.llm.chat(messages, max_tokens=15000)
            npc_response = response
            
        except Exception as e:
            logger.error(f"LLM error in NPC dialogue: {e}")
            # Fallback response
            npc_response = f"*{npc['name']} regards you thoughtfully but says nothing.*"
        
        # Add NPC response to history
        self.parent.conversation_history.append({
            "role": "assistant",
            "content": npc_response
        })
        
        embed = discord.Embed(
            title=f"💬 Talking with {npc['name']}",
            color=discord.Color.purple()
        )
        embed.add_field(
            name=f"You say:",
            value=user_message[:500],
            inline=False
        )
        embed.add_field(
            name=f"{npc['name']} responds:",
            value=npc_response[:1000],
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self.parent)


class NPCs(commands.Cog):
    """NPC management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    npc_group = app_commands.Group(
        name="npc", 
        description="NPC commands",
        guild_only=True
    )
    
    @npc_group.command(name="create", description="Create a new NPC (DM only)")
    @app_commands.describe(npc_type="Type of NPC to create")
    @app_commands.choices(npc_type=[
        app_commands.Choice(name="Merchant", value="merchant"),
        app_commands.Choice(name="Guard", value="guard"),
        app_commands.Choice(name="Innkeeper", value="innkeeper"),
        app_commands.Choice(name="Wizard", value="wizard"),
        app_commands.Choice(name="Villain", value="villain"),
        app_commands.Choice(name="Peasant", value="peasant"),
        app_commands.Choice(name="Custom", value="custom"),
    ])
    async def create_npc(
        self,
        interaction: discord.Interaction,
        npc_type: str = "custom"
    ):
        """Create a new NPC"""
        modal = CreateNPCModal(self.bot, npc_type)
        await interaction.response.send_modal(modal)
    
    @npc_group.command(name="quick", description="Quickly create an NPC from a template")
    @app_commands.describe(
        template="NPC template to use",
        name="Name of the NPC",
        location="Where the NPC is located"
    )
    @app_commands.choices(template=[
        app_commands.Choice(name="Merchant", value="merchant"),
        app_commands.Choice(name="Guard", value="guard"),
        app_commands.Choice(name="Innkeeper", value="innkeeper"),
        app_commands.Choice(name="Wizard", value="wizard"),
        app_commands.Choice(name="Villain", value="villain"),
        app_commands.Choice(name="Peasant", value="peasant"),
    ])
    async def quick_create_npc(
        self,
        interaction: discord.Interaction,
        template: str,
        name: str,
        location: str = "Unknown"
    ):
        """Quick NPC creation from template"""
        templ = NPC_TEMPLATES.get(template)
        if not templ:
            await interaction.response.send_message(
                "❌ Invalid template!",
                ephemeral=True
            )
            return
        
        npc_id = await self.db.create_npc(
            guild_id=interaction.guild.id,
            name=name,
            description=f"A typical {template}.",
            personality=templ['personality'],
            location=location,
            npc_type=template,
            created_by=interaction.user.id
        )
        
        embed = discord.Embed(
            title=f"✅ NPC Created: {name}",
            description=f"A {template} has been added to the game!",
            color=discord.Color.green()
        )
        embed.add_field(name="Location", value=location, inline=True)
        embed.add_field(name="NPC ID", value=str(npc_id), inline=True)
        embed.add_field(name="Personality", value=templ['personality'], inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @npc_group.command(name="list", description="List all NPCs")
    @app_commands.describe(location="Filter by location")
    async def list_npcs(
        self,
        interaction: discord.Interaction,
        location: Optional[str] = None
    ):
        """List all NPCs in the guild"""
        npcs = await self.db.get_npcs(interaction.guild.id, location=location)
        
        if not npcs:
            await interaction.response.send_message(
                "📜 No NPCs found!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎭 NPCs",
            description=f"NPCs in {location if location else 'this realm'}:",
            color=discord.Color.purple()
        )
        
        for npc in npcs[:15]:  # Limit display
            embed.add_field(
                name=f"[{npc['id']}] {npc['name']}",
                value=f"📍 {npc['location']}\n{npc['description'][:80]}...",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    @npc_group.command(name="interact", description="Start a conversation with an NPC")
    @app_commands.describe(npc_id="The ID of the NPC to interact with")
    async def interact_npc(self, interaction: discord.Interaction, npc_id: int):
        """Start NPC interaction"""
        npc = await self.db.get_npc(npc_id)
        
        if not npc:
            await interaction.response.send_message(
                "❌ NPC not found!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"🎭 {npc['name']}",
            description=npc['description'],
            color=discord.Color.purple()
        )
        embed.add_field(name="Location", value=npc['location'], inline=True)
        
        # Get initial greeting based on type
        template = NPC_TEMPLATES.get(npc['npc_type'], {})
        greeting = template.get('default_dialogue', f"*{npc['name']} acknowledges your presence.*")
        embed.add_field(name="Greeting", value=greeting, inline=False)
        
        view = NPCDialogueView(self.bot, npc, interaction.channel.id)
        await interaction.response.send_message(embed=embed, view=view)
    
    @npc_group.command(name="summon", description="Summon an NPC to the current location")
    @app_commands.describe(
        npc_id="The ID of the NPC to summon",
        location="New location for the NPC"
    )
    async def summon_npc(
        self,
        interaction: discord.Interaction,
        npc_id: int,
        location: str
    ):
        """Move an NPC to a new location"""
        npc = await self.db.get_npc(npc_id)
        
        if not npc:
            await interaction.response.send_message(
                "❌ NPC not found!",
                ephemeral=True
            )
            return
        
        await self.db.update_npc(npc_id, location=location)
        
        await interaction.response.send_message(
            f"📍 **{npc['name']}** has been moved to **{location}**!"
        )
    
    @npc_group.command(name="edit", description="Edit an NPC's details")
    @app_commands.describe(
        npc_id="The ID of the NPC to edit",
        name="New name",
        description="New description",
        personality="New personality",
        location="New location"
    )
    async def edit_npc(
        self,
        interaction: discord.Interaction,
        npc_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        personality: Optional[str] = None,
        location: Optional[str] = None
    ):
        """Edit an existing NPC"""
        npc = await self.db.get_npc(npc_id)
        
        if not npc:
            await interaction.response.send_message(
                "❌ NPC not found!",
                ephemeral=True
            )
            return
        
        updates = {}
        if name:
            updates['name'] = name
        if description:
            updates['description'] = description
        if personality:
            updates['personality'] = personality
        if location:
            updates['location'] = location
        
        if not updates:
            await interaction.response.send_message(
                "❌ No changes specified!",
                ephemeral=True
            )
            return
        
        await self.db.update_npc(npc_id, **updates)
        
        await interaction.response.send_message(
            f"✅ **{npc['name']}** has been updated!"
        )
    
    @npc_group.command(name="delete", description="Delete an NPC (DM only)")
    @app_commands.describe(npc_id="The ID of the NPC to delete")
    async def delete_npc(self, interaction: discord.Interaction, npc_id: int):
        """Delete an NPC"""
        npc = await self.db.get_npc(npc_id)
        
        if not npc:
            await interaction.response.send_message(
                "❌ NPC not found!",
                ephemeral=True
            )
            return
        
        await self.db.delete_npc(npc_id)
        
        await interaction.response.send_message(
            f"🗑️ NPC **{npc['name']}** has been deleted!"
        )


async def setup(bot):
    await bot.add_cog(NPCs(bot))
