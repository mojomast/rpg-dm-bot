"""
RPG DM Bot - DM Chat Cog
Handles AI Dungeon Master interactions with tool execution
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
from typing import Optional
from datetime import datetime

logger = logging.getLogger('rpg.dm_chat')

# Maximum tool execution rounds
MAX_TOOL_ROUNDS = 5

# Import proactive DM guidelines
from src.prompts import PROACTIVE_DM_GUIDELINES


class DMChat(commands.Cog):
    """AI Dungeon Master chat handling"""
    
    def __init__(self, bot):
        self.bot = bot
        # Channel conversation histories
        self.histories = {}
        # Max history length per channel
        self.max_history = 50
        # Track last activity per channel for proactive prompting
        self.last_activity = {}
    
    @property
    def db(self):
        return self.bot.db
    
    @property
    def llm(self):
        return self.bot.llm
    
    @property
    def tools(self):
        return self.bot.tools
    
    def get_history(self, channel_id: int) -> list:
        """Get conversation history for a channel"""
        if channel_id not in self.histories:
            self.histories[channel_id] = []
        return self.histories[channel_id]
    
    def add_to_history(self, channel_id: int, message: dict):
        """Add a message to channel history"""
        history = self.get_history(channel_id)
        history.append(message)
        
        # Trim if too long
        if len(history) > self.max_history:
            # Keep system messages and recent ones
            self.histories[channel_id] = history[-self.max_history:]
    
    def clear_history(self, channel_id: int):
        """Clear channel history"""
        self.histories[channel_id] = []
    
    async def get_game_context(
        self,
        guild_id: int,
        user_id: int,
        channel_id: int
    ) -> str:
        """Build context about the current game state"""
        context_parts = []
        
        # Get user's character
        char = await self.db.get_active_character(user_id, guild_id)
        if char:
            context_parts.append(f"""
PLAYER CHARACTER:
- Name: {char['name']}
- Class: {char['char_class']} | Race: {char['race']}
- Level: {char['level']} | XP: {char['xp']}
- HP: {char['hp']}/{char['max_hp']}
- Stats: STR {char['strength']}, DEX {char['dexterity']}, CON {char['constitution']}, INT {char['intelligence']}, WIS {char['wisdom']}, CHA {char['charisma']}
- Gold: {char['gold']}
""")
        
        # Get active session
        sessions = await self.db.get_sessions(guild_id, status='active')
        if sessions:
            session = sessions[0]
            context_parts.append(f"\nACTIVE SESSION: {session['name']}")
            
            # Get session quest
            if session.get('current_quest_id'):
                quest = await self.db.get_quest(session['current_quest_id'])
                if quest:
                    stages = await self.db.get_quest_stages(quest['id'])
                    current_stage = stages[quest['current_stage']] if quest['current_stage'] < len(stages) else None
                    
                    context_parts.append(f"""
CURRENT QUEST: {quest['title']}
Description: {quest['description']}
Difficulty: {quest['difficulty']}
Stage: {quest['current_stage'] + 1}/{len(stages)}
""")
                    if current_stage:
                        context_parts.append(f"""
CURRENT STAGE: {current_stage['title']}
{current_stage['description']}
""")
        
        # Get active combat
        combat = await self.db.get_active_combat(guild_id, channel_id)
        if combat:
            participants = await self.db.get_combat_participants(combat['id'])
            context_parts.append(f"\nACTIVE COMBAT:")
            context_parts.append(f"Turn: {combat['current_turn']}")
            context_parts.append("Combatants:")
            for p in participants:
                char_info = await self.db.get_character(p['character_id'])
                if char_info:
                    context_parts.append(f"- {char_info['name']}: {p['current_hp']} HP, Initiative {p['initiative']}")
        
        return "\n".join(context_parts) if context_parts else "No active game context."
    
    async def process_dm_message(
        self,
        message: discord.Message,
        user_message: str
    ) -> str:
        """Process a message through the AI DM with tool support"""
        channel_id = message.channel.id
        guild_id = message.guild.id
        user_id = message.author.id
        
        # Track activity
        self.last_activity[channel_id] = datetime.utcnow()
        
        # Get game context
        game_context = await self.get_game_context(guild_id, user_id, channel_id)
        
        # Build system prompt with context and proactive guidelines
        system_prompt = f"""{self.bot.prompts.get_dm_system_prompt()}

{PROACTIVE_DM_GUIDELINES}

CURRENT GAME STATE:
{game_context}

TOOLS AVAILABLE:
You have access to tools for managing the game. Use them when players want to:
- Create/modify characters
- Manage inventory and items  
- Roll dice for checks and combat
- Control NPCs and dialogue
- Manage quests and progression
- Run combat encounters

Always use dice rolls for skill checks and combat. Make the game interactive and engaging.

CRITICAL: Always end your response with a prompt for player action. Keep the game moving!
"""
        
        # Get conversation history
        history = self.get_history(channel_id)
        
        # Add user message to history
        user_msg = {"role": "user", "content": f"[{message.author.display_name}]: {user_message}"}
        self.add_to_history(channel_id, user_msg)
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": system_prompt},
            *history
        ]
        
        # Get tool schemas
        tool_schemas = self.bot.tool_schemas.get_all_schemas()
        
        # Process with tool loop
        response_text = ""
        
        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                response = await self.llm.chat_with_tools(
                    messages=messages,
                    tools=tool_schemas
                )
                
                # Check for tool calls
                tool_calls = response.get('tool_calls', [])
                content = response.get('content', '')
                
                if not tool_calls:
                    # No more tools, we have final response
                    response_text = content
                    break
                
                # Execute tools
                for tool_call in tool_calls:
                    tool_name = tool_call['function']['name']
                    try:
                        tool_args = json.loads(tool_call['function']['arguments'])
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Build context for tool execution
                    context = {
                        'guild_id': guild_id,
                        'user_id': user_id,
                        'channel_id': channel_id
                    }
                    
                    # Execute the tool
                    tool_result = await self.tools.execute_tool(
                        tool_name,
                        tool_args,
                        context
                    )
                    
                    # Add tool call and result to messages
                    messages.append({
                        "role": "assistant",
                        "content": content,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                    })
                
            except Exception as e:
                logger.error(f"Error in DM chat: {e}")
                response_text = f"*The Dungeon Master pauses, gathering their thoughts...* (Error: {str(e)[:100]})"
                break
        
        # Add response to history
        if response_text:
            self.add_to_history(channel_id, {"role": "assistant", "content": response_text})
        
        return response_text or "*The Dungeon Master remains silent.*"
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages in designated DM channels or mentions"""
        # Ignore bots
        if message.author.bot:
            return
        
        # Ignore DMs
        if not message.guild:
            return
        
        # Check if bot was mentioned or if it's a DM channel
        bot_mentioned = self.bot.user in message.mentions
        is_dm_channel = "dungeon-master" in message.channel.name.lower() or "dm-chat" in message.channel.name.lower()
        
        if not (bot_mentioned or is_dm_channel):
            return
        
        # Remove bot mention from message
        content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        content = message.content.replace(f'<@!{self.bot.user.id}>', '').strip()
        
        if not content:
            content = "Hello!"
        
        async with message.channel.typing():
            response = await self.process_dm_message(message, content)
            
            # Split response if too long
            if len(response) > 2000:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.reply(chunk)
            else:
                await message.reply(response)
    
    @app_commands.command(name="dm", description="Talk to the Dungeon Master - describe what you want to do!")
    @app_commands.describe(message="What do you want to say or do? Be creative!")
    async def dm_command(self, interaction: discord.Interaction, message: str):
        """Interact with the AI Dungeon Master"""
        await interaction.response.defer()
        
        # Check if user has a character
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            # Prompt to create character
            embed = discord.Embed(
                title="🎭 Hold, Adventurer!",
                description=(
                    "You haven't created a character yet!\n\n"
                    "Use `/game menu` to create your character and join a game.\n"
                    "The Dungeon Master awaits your arrival!"
                ),
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Create a fake message object for processing
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = message
        
        fake_msg = FakeMessage(interaction)
        response = await self.process_dm_message(fake_msg, message)
        
        # Create embed for response
        embed = discord.Embed(
            description=response[:4000],
            color=discord.Color.dark_purple()
        )
        embed.set_author(
            name="🎭 Dungeon Master",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        embed.set_footer(text=f"{char['name']}: \"{message[:50]}{'...' if len(message) > 50 else ''}\"")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="action", description="Quick actions for common RPG activities")
    @app_commands.describe(action="What action do you want to take?")
    @app_commands.choices(action=[
        app_commands.Choice(name="🔍 Look around", value="look"),
        app_commands.Choice(name="👂 Listen carefully", value="listen"),
        app_commands.Choice(name="🚪 Search for secrets", value="search"),
        app_commands.Choice(name="🗣️ Talk to someone nearby", value="talk"),
        app_commands.Choice(name="🎒 Check my inventory", value="inventory"),
        app_commands.Choice(name="❓ What are my options?", value="options"),
        app_commands.Choice(name="⏭️ Continue forward", value="continue"),
    ])
    async def quick_action(self, interaction: discord.Interaction, action: str):
        """Quick action command for common activities"""
        await interaction.response.defer()
        
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.followup.send(
                "❌ Create a character first with `/game menu`!",
                ephemeral=True
            )
            return
        
        action_prompts = {
            'look': f"{char['name']} looks around carefully, taking in the surroundings. Describe what I see.",
            'listen': f"{char['name']} stops and listens carefully. What do I hear?",
            'search': f"{char['name']} searches the area for hidden objects, traps, or secrets. Roll Investigation/Perception and tell me what I find.",
            'talk': f"{char['name']} approaches the nearest person or creature to talk. Who is nearby and what do they say?",
            'inventory': f"What items does {char['name']} have in their inventory? List them out.",
            'options': f"What are {char['name']}'s options right now? Give me 3-4 things I could do.",
            'continue': f"{char['name']} continues forward with the current objective. What happens next?"
        }
        
        prompt = action_prompts.get(action, "What happens next?")
        
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        fake_msg = FakeMessage(interaction)
        response = await self.process_dm_message(fake_msg, prompt)
        
        action_titles = {
            'look': "👁️ Looking Around",
            'listen': "👂 Listening",
            'search': "🔍 Searching",
            'talk': "🗣️ Conversation",
            'inventory': "🎒 Inventory",
            'options': "❓ Your Options",
            'continue': "⏭️ Moving Forward"
        }
        
        embed = discord.Embed(
            title=action_titles.get(action, "Action"),
            description=response[:4000],
            color=discord.Color.dark_purple()
        )
        embed.set_footer(text=f"Playing as {char['name']}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="narrate", description="Have the DM narrate a scene")
    @app_commands.describe(
        scene="Description of the scene to narrate",
        tone="The tone of the narration"
    )
    @app_commands.choices(tone=[
        app_commands.Choice(name="Epic", value="epic"),
        app_commands.Choice(name="Mysterious", value="mysterious"),
        app_commands.Choice(name="Comedic", value="comedic"),
        app_commands.Choice(name="Tense", value="tense"),
        app_commands.Choice(name="Peaceful", value="peaceful"),
    ])
    async def narrate(
        self,
        interaction: discord.Interaction,
        scene: str,
        tone: str = "epic"
    ):
        """Have the DM narrate a scene"""
        await interaction.response.defer()
        
        prompt = f"Narrate this scene in a {tone} tone: {scene}"
        
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        fake_msg = FakeMessage(interaction)
        response = await self.process_dm_message(fake_msg, prompt)
        
        embed = discord.Embed(
            title=f"📜 {tone.title()} Narration",
            description=response[:4000],
            color=discord.Color.dark_gold()
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="check", description="Make a skill check")
    @app_commands.describe(
        skill="The skill to check",
        difficulty="The difficulty class (DC)"
    )
    @app_commands.choices(skill=[
        app_commands.Choice(name="Strength", value="strength"),
        app_commands.Choice(name="Dexterity", value="dexterity"),
        app_commands.Choice(name="Constitution", value="constitution"),
        app_commands.Choice(name="Intelligence", value="intelligence"),
        app_commands.Choice(name="Wisdom", value="wisdom"),
        app_commands.Choice(name="Charisma", value="charisma"),
        app_commands.Choice(name="Perception", value="perception"),
        app_commands.Choice(name="Stealth", value="stealth"),
        app_commands.Choice(name="Persuasion", value="persuasion"),
        app_commands.Choice(name="Intimidation", value="intimidation"),
        app_commands.Choice(name="Investigation", value="investigation"),
        app_commands.Choice(name="Athletics", value="athletics"),
        app_commands.Choice(name="Acrobatics", value="acrobatics"),
    ])
    async def skill_check(
        self,
        interaction: discord.Interaction,
        skill: str,
        difficulty: Optional[int] = None
    ):
        """Make a skill check with DM narration"""
        await interaction.response.defer()
        
        dc_text = f" against DC {difficulty}" if difficulty else ""
        prompt = f"I want to make a {skill} check{dc_text}. Roll the dice and narrate the result."
        
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        fake_msg = FakeMessage(interaction)
        response = await self.process_dm_message(fake_msg, prompt)
        
        embed = discord.Embed(
            title=f"🎲 {skill.title()} Check",
            description=response[:4000],
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="dm_clear", description="Clear the DM conversation history")
    async def clear_dm_history(self, interaction: discord.Interaction):
        """Clear conversation history"""
        self.clear_history(interaction.channel.id)
        
        await interaction.response.send_message(
            "🧹 The Dungeon Master's memory has been cleared for this channel.",
            ephemeral=True
        )
    
    @app_commands.command(name="scene", description="Set the scene for the adventure")
    @app_commands.describe(description="Description of the current scene/location")
    async def set_scene(self, interaction: discord.Interaction, description: str):
        """Set a scene for the DM to build upon"""
        await interaction.response.defer()
        
        prompt = f"Set the following scene for our adventure and describe what the players see, hear, and feel: {description}"
        
        class FakeMessage:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.guild = interaction.guild
                self.author = interaction.user
                self.content = prompt
        
        fake_msg = FakeMessage(interaction)
        response = await self.process_dm_message(fake_msg, prompt)
        
        embed = discord.Embed(
            title="🏰 Scene Set",
            description=response[:4000],
            color=discord.Color.dark_green()
        )
        
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DMChat(bot))
