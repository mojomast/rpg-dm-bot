"""
Party Member Bot - Interview Cog
Handles character creation interview by relaying messages between DM bot and owner
"""

import discord
from discord.ext import commands
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger('party_member.interview')


class InterviewState(Enum):
    """States of the character creation interview"""
    IDLE = auto()
    WAITING_FOR_GUILD = auto()
    WAITING_FOR_RACE = auto()
    WAITING_FOR_CLASS = auto()
    WAITING_FOR_STATS = auto()
    WAITING_FOR_NAME = auto()
    WAITING_FOR_BACKSTORY = auto()
    WAITING_FOR_PERSONALITY = auto()
    WAITING_FOR_PLAYSTYLE = auto()
    COMPLETE = auto()


# Available options from the RPG DM bot
RACES = ["Human", "Elf", "Dwarf", "Halfling", "Orc", "Tiefling", "Dragonborn", "Gnome"]
CLASSES = ["Warrior", "Mage", "Rogue", "Cleric", "Ranger", "Bard", "Paladin", "Warlock"]
PLAY_STYLES = ["aggressive", "defensive", "balanced", "cautious", "reckless"]
STAT_METHODS = ["roll", "standard"]


class Interview(commands.Cog):
    """Handles character creation interview process"""
    
    def __init__(self, bot):
        self.bot = bot
        self.interview_sessions: Dict[int, Dict[str, Any]] = {}  # user_id -> session data
    
    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get an interview session for a user"""
        return self.interview_sessions.get(user_id)
    
    def create_session(self, user_id: int) -> Dict[str, Any]:
        """Create a new interview session"""
        session = {
            'state': InterviewState.WAITING_FOR_GUILD,
            'guild_id': None,
            'character': {
                'name': '',
                'race': '',
                'char_class': '',
                'backstory': '',
                'personality': '',
                'play_style': 'balanced',
                'stats': {}
            },
            'started_at': datetime.utcnow().isoformat()
        }
        self.interview_sessions[user_id] = session
        return session
    
    def end_session(self, user_id: int):
        """End an interview session"""
        if user_id in self.interview_sessions:
            del self.interview_sessions[user_id]
    
    async def handle_dm(self, message: discord.Message):
        """Handle DM messages that might be part of an interview"""
        session = self.get_session(message.author.id)
        if not session:
            return
        
        await self.process_interview_response(message, session)
    
    async def start_interview(self, ctx: commands.Context):
        """Start the character creation interview"""
        # Check if already in an interview
        if self.get_session(ctx.author.id):
            await ctx.send("❌ You already have an interview in progress! Use `!pm cancel` to cancel it.")
            return
        
        session = self.create_session(ctx.author.id)
        
        embed = discord.Embed(
            title="🎭 Character Creation Interview",
            description="Let's create a character for this bot to play!\n\n"
                       "I'll ask you some questions and then register the character with the RPG DM bot.",
            color=discord.Color.purple()
        )
        
        # Build guild selection
        guilds = self.bot.guilds
        if not guilds:
            await ctx.send("❌ This bot isn't in any servers! Add it to a server first.")
            self.end_session(ctx.author.id)
            return
        
        guild_list = "\n".join([f"**{i+1}.** {g.name}" for i, g in enumerate(guilds)])
        embed.add_field(
            name="Step 1: Select Server",
            value=f"Which server will this character play in?\n\n{guild_list}\n\nReply with the number.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def process_interview_response(self, message: discord.Message, session: Dict[str, Any]):
        """Process a response during the interview"""
        content = message.content.strip()
        state = session['state']
        
        if content.lower() == 'cancel':
            self.end_session(message.author.id)
            await message.channel.send("❌ Interview cancelled.")
            return
        
        if state == InterviewState.WAITING_FOR_GUILD:
            await self._handle_guild_selection(message, session, content)
        elif state == InterviewState.WAITING_FOR_RACE:
            await self._handle_race_selection(message, session, content)
        elif state == InterviewState.WAITING_FOR_CLASS:
            await self._handle_class_selection(message, session, content)
        elif state == InterviewState.WAITING_FOR_STATS:
            await self._handle_stats_selection(message, session, content)
        elif state == InterviewState.WAITING_FOR_NAME:
            await self._handle_name_input(message, session, content)
        elif state == InterviewState.WAITING_FOR_BACKSTORY:
            await self._handle_backstory_input(message, session, content)
        elif state == InterviewState.WAITING_FOR_PERSONALITY:
            await self._handle_personality_input(message, session, content)
        elif state == InterviewState.WAITING_FOR_PLAYSTYLE:
            await self._handle_playstyle_input(message, session, content)
    
    async def _handle_guild_selection(self, message: discord.Message, session: Dict[str, Any], content: str):
        """Handle guild selection"""
        try:
            index = int(content) - 1
            guilds = list(self.bot.guilds)
            if 0 <= index < len(guilds):
                guild = guilds[index]
                session['guild_id'] = guild.id
                session['guild_name'] = guild.name
                session['state'] = InterviewState.WAITING_FOR_RACE
                
                # Show race selection
                race_list = "\n".join([f"**{i+1}.** {r}" for i, r in enumerate(RACES)])
                embed = discord.Embed(
                    title="🧝 Choose Race",
                    description=f"Selected server: **{guild.name}**\n\n"
                               f"Now choose your character's race:\n\n{race_list}\n\n"
                               f"Reply with the number.",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("❌ Invalid selection. Please enter a valid number.")
        except ValueError:
            await message.channel.send("❌ Please enter a number.")
    
    async def _handle_race_selection(self, message: discord.Message, session: Dict[str, Any], content: str):
        """Handle race selection"""
        try:
            index = int(content) - 1
            if 0 <= index < len(RACES):
                race = RACES[index]
                session['character']['race'] = race
                session['state'] = InterviewState.WAITING_FOR_CLASS
                
                # Show class selection
                class_list = "\n".join([f"**{i+1}.** {c}" for i, c in enumerate(CLASSES)])
                embed = discord.Embed(
                    title="⚔️ Choose Class",
                    description=f"Race: **{race}**\n\n"
                               f"Now choose your character's class:\n\n{class_list}\n\n"
                               f"Reply with the number.",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("❌ Invalid selection. Please enter a valid number (1-8).")
        except ValueError:
            await message.channel.send("❌ Please enter a number.")
    
    async def _handle_class_selection(self, message: discord.Message, session: Dict[str, Any], content: str):
        """Handle class selection"""
        try:
            index = int(content) - 1
            if 0 <= index < len(CLASSES):
                char_class = CLASSES[index]
                session['character']['char_class'] = char_class
                session['state'] = InterviewState.WAITING_FOR_STATS
                
                embed = discord.Embed(
                    title="🎲 Choose Stat Method",
                    description=f"Race: **{session['character']['race']}**\n"
                               f"Class: **{char_class}**\n\n"
                               f"How would you like to determine stats?\n\n"
                               f"**1.** 🎲 Roll (4d6 drop lowest - exciting!)\n"
                               f"**2.** 📊 Standard Array (15, 14, 13, 12, 10, 8)\n\n"
                               f"Reply with 1 or 2.",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("❌ Invalid selection. Please enter a valid number (1-8).")
        except ValueError:
            await message.channel.send("❌ Please enter a number.")
    
    async def _handle_stats_selection(self, message: discord.Message, session: Dict[str, Any], content: str):
        """Handle stat method selection"""
        import random
        
        if content == '1':
            # Roll stats
            stats = {}
            stat_names = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
            rolls_display = []
            
            for stat in stat_names:
                rolls = sorted([random.randint(1, 6) for _ in range(4)], reverse=True)
                value = sum(rolls[:3])
                stats[stat] = value
                rolls_display.append(f"**{stat.upper()[:3]}**: {value} (rolled {rolls})")
            
            session['character']['stats'] = stats
            session['state'] = InterviewState.WAITING_FOR_NAME
            
            embed = discord.Embed(
                title="🎲 Stats Rolled!",
                description="\n".join(rolls_display),
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next: Character Name",
                value="What is your character's name?",
                inline=False
            )
            await message.channel.send(embed=embed)
            
        elif content == '2':
            # Standard array
            stats = {
                'strength': 15,
                'dexterity': 14,
                'constitution': 13,
                'intelligence': 12,
                'wisdom': 10,
                'charisma': 8
            }
            session['character']['stats'] = stats
            session['state'] = InterviewState.WAITING_FOR_NAME
            
            embed = discord.Embed(
                title="📊 Standard Array Applied",
                description="STR: 15 | DEX: 14 | CON: 13\nINT: 12 | WIS: 10 | CHA: 8",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next: Character Name",
                value="What is your character's name?",
                inline=False
            )
            await message.channel.send(embed=embed)
        else:
            await message.channel.send("❌ Please enter 1 or 2.")
    
    async def _handle_name_input(self, message: discord.Message, session: Dict[str, Any], content: str):
        """Handle character name input"""
        if len(content) < 2:
            await message.channel.send("❌ Name must be at least 2 characters.")
            return
        if len(content) > 32:
            await message.channel.send("❌ Name must be 32 characters or less.")
            return
        
        session['character']['name'] = content
        session['state'] = InterviewState.WAITING_FOR_BACKSTORY
        
        embed = discord.Embed(
            title=f"✨ Welcome, {content}!",
            description=f"**{content}** the {session['character']['race']} {session['character']['char_class']}\n\n"
                       f"Now, tell me about your character's backstory.\n"
                       f"(Type 'skip' to skip, or enter a backstory up to 500 characters)",
            color=discord.Color.blue()
        )
        await message.channel.send(embed=embed)
    
    async def _handle_backstory_input(self, message: discord.Message, session: Dict[str, Any], content: str):
        """Handle backstory input"""
        if content.lower() != 'skip':
            session['character']['backstory'] = content[:500]
        
        session['state'] = InterviewState.WAITING_FOR_PERSONALITY
        
        embed = discord.Embed(
            title="🎭 Personality",
            description="Describe your character's personality traits.\n"
                       "This helps the bot roleplay your character better!\n\n"
                       "(Type 'skip' to skip, or describe personality traits)",
            color=discord.Color.blue()
        )
        await message.channel.send(embed=embed)
    
    async def _handle_personality_input(self, message: discord.Message, session: Dict[str, Any], content: str):
        """Handle personality input"""
        if content.lower() != 'skip':
            session['character']['personality'] = content[:500]
        
        session['state'] = InterviewState.WAITING_FOR_PLAYSTYLE
        
        style_list = "\n".join([f"**{i+1}.** {s.title()}" for i, s in enumerate(PLAY_STYLES)])
        embed = discord.Embed(
            title="⚔️ Play Style",
            description=f"How should your character approach challenges?\n\n{style_list}\n\n"
                       f"Reply with the number.",
            color=discord.Color.blue()
        )
        await message.channel.send(embed=embed)
    
    async def _handle_playstyle_input(self, message: discord.Message, session: Dict[str, Any], content: str):
        """Handle play style input"""
        try:
            index = int(content) - 1
            if 0 <= index < len(PLAY_STYLES):
                session['character']['play_style'] = PLAY_STYLES[index]
                session['state'] = InterviewState.COMPLETE
                
                await self._complete_interview(message, session)
            else:
                await message.channel.send("❌ Invalid selection. Please enter 1-5.")
        except ValueError:
            await message.channel.send("❌ Please enter a number (1-5).")
    
    async def _complete_interview(self, message: discord.Message, session: Dict[str, Any]):
        """Complete the interview and save the character"""
        char = session['character']
        
        # Save to bot's character data
        self.bot.character_data = {
            'name': char['name'],
            'race': char['race'],
            'class': char['char_class'],
            'level': 1,
            'backstory': char.get('backstory', ''),
            'personality': char.get('personality', ''),
            'play_style': char.get('play_style', 'balanced'),
            'stats': char.get('stats', {}),
            'guild_id': session['guild_id'],
            'guild_name': session.get('guild_name', 'Unknown'),
            'created_at': datetime.utcnow().isoformat()
        }
        
        await self.bot.save_character_data()
        
        # Update bot presence
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=f"as {char['name']} | DM me to configure"
        )
        await self.bot.change_presence(activity=activity)
        
        # Build summary embed
        stats = char.get('stats', {})
        embed = discord.Embed(
            title="🎉 Character Created!",
            description=f"**{char['name']}**\n"
                       f"Level 1 {char['race']} {char['char_class']}",
            color=discord.Color.green()
        )
        
        if stats:
            embed.add_field(
                name="📊 Stats",
                value=f"STR: {stats.get('strength', 10)} | DEX: {stats.get('dexterity', 10)} | CON: {stats.get('constitution', 10)}\n"
                      f"INT: {stats.get('intelligence', 10)} | WIS: {stats.get('wisdom', 10)} | CHA: {stats.get('charisma', 10)}",
                inline=False
            )
        
        if char.get('backstory'):
            embed.add_field(
                name="📜 Backstory",
                value=char['backstory'][:200] + ('...' if len(char['backstory']) > 200 else ''),
                inline=False
            )
        
        if char.get('personality'):
            embed.add_field(
                name="🎭 Personality",
                value=char['personality'][:200] + ('...' if len(char['personality']) > 200 else ''),
                inline=False
            )
        
        embed.add_field(
            name="⚔️ Play Style",
            value=char.get('play_style', 'balanced').title(),
            inline=True
        )
        
        embed.add_field(
            name="🏰 Server",
            value=session.get('guild_name', 'Unknown'),
            inline=True
        )
        
        embed.add_field(
            name="📋 Next Steps",
            value="1. Use `!pm register` to create this character in the RPG DM bot\n"
                  "2. Use `!pm join #channel` to join a game session\n"
                  "3. Use `!pm autoplay on` to enable auto-play mode",
            inline=False
        )
        
        await message.channel.send(embed=embed)
        
        # Clean up session
        self.end_session(message.author.id)


async def setup(bot):
    await bot.add_cog(Interview(bot))
