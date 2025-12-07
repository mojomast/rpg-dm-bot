"""
Party Member Bot - Main Entry Point
A Discord bot that acts as a player character for automated RPG testing
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import json

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Generate log filename with timestamp
log_filename = f"logs/party_member_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

logger = logging.getLogger('party_member')
logger.info(f"Logging to file: {log_filename}")

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = os.getenv('OWNER_ID')  # Discord user ID of the bot owner
DM_BOT_ID = os.getenv('DM_BOT_ID')  # Discord user ID of the RPG DM bot
CHARACTER_NAME = os.getenv('CHARACTER_NAME', 'Adventurer')
DATA_PATH = os.getenv('DATA_PATH', 'data/character.json')

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables!")


class PartyMemberBot(commands.Bot):
    """A Discord bot that acts as a player character in RPG sessions"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.dm_messages = True
        
        super().__init__(
            command_prefix='!pm ',
            intents=intents,
            help_command=None
        )
        
        self.owner_id_config = int(OWNER_ID) if OWNER_ID else None
        self.dm_bot_id = int(DM_BOT_ID) if DM_BOT_ID else None
        self.character_data = {}
        self.interview_state = {}  # Tracks ongoing character creation interviews
        self.active_sessions = {}  # Tracks which channels the bot is active in
        self.auto_play_mode = {}  # Whether to auto-respond in sessions
        self._started_at = None
        self._setup_done = False
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        # Load character data if it exists
        await self.load_character_data()
        
        # Load cogs
        try:
            await self.load_extension('src.cogs.interview')
            logger.info("Loaded interview cog")
        except Exception as e:
            logger.error(f"Failed to load interview cog: {e}")
            
        try:
            await self.load_extension('src.cogs.gameplay')
            logger.info("Loaded gameplay cog")
        except Exception as e:
            logger.error(f"Failed to load gameplay cog: {e}")
            
        try:
            await self.load_extension('src.cogs.owner_commands')
            logger.info("Loaded owner commands cog")
        except Exception as e:
            logger.error(f"Failed to load owner commands cog: {e}")
        
        logger.info("Setup hook completed")
    
    async def load_character_data(self):
        """Load character data from file"""
        if os.path.exists(DATA_PATH):
            try:
                with open(DATA_PATH, 'r') as f:
                    self.character_data = json.load(f)
                logger.info(f"Loaded character data: {self.character_data.get('name', 'Unknown')}")
            except Exception as e:
                logger.error(f"Failed to load character data: {e}")
                self.character_data = {}
        else:
            logger.info("No existing character data found")
    
    async def save_character_data(self):
        """Save character data to file"""
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        try:
            with open(DATA_PATH, 'w') as f:
                json.dump(self.character_data, f, indent=2)
            logger.info(f"Saved character data: {self.character_data.get('name', 'Unknown')}")
        except Exception as e:
            logger.error(f"Failed to save character data: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        self._started_at = datetime.now(timezone.utc)
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Set presence based on character
        char_name = self.character_data.get('name', CHARACTER_NAME)
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=f"as {char_name} | DM me to configure"
        )
        await self.change_presence(activity=activity)
        
        # DM the owner on first connect
        if self.owner_id_config and not self._setup_done:
            await self.notify_owner_on_connect()
            self._setup_done = True
    
    async def notify_owner_on_connect(self):
        """Send a DM to the owner when the bot connects"""
        try:
            owner = await self.fetch_user(self.owner_id_config)
            if owner:
                embed = discord.Embed(
                    title="🤖 Party Member Bot Connected!",
                    description="I'm online and ready to play!",
                    color=discord.Color.green()
                )
                
                if self.character_data:
                    char = self.character_data
                    embed.add_field(
                        name="📜 Current Character",
                        value=f"**{char.get('name', 'Unknown')}**\n"
                              f"Level {char.get('level', 1)} {char.get('race', '?')} {char.get('class', '?')}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⚠️ No Character",
                        value="No character configured yet. Use `!pm create` to start character creation!",
                        inline=False
                    )
                
                embed.add_field(
                    name="📋 Commands",
                    value="• `!pm create` - Start character creation interview\n"
                          "• `!pm status` - View bot and character status\n"
                          "• `!pm join #channel` - Join a game session\n"
                          "• `!pm leave #channel` - Leave a game session\n"
                          "• `!pm autoplay on/off` - Toggle auto-play mode\n"
                          "• `!pm say <message>` - Speak as your character\n"
                          "• `!pm help` - Show all commands",
                    inline=False
                )
                
                embed.set_footer(text=f"Bot ID: {self.user.id}")
                
                await owner.send(embed=embed)
                logger.info(f"Sent connection notification to owner {owner.name}")
        except Exception as e:
            logger.error(f"Failed to notify owner: {e}")
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore messages from self
        if message.author.id == self.user.id:
            return
        
        # Ignore messages before bot was ready
        if self._started_at is None:
            return
        
        # Handle DMs from owner for configuration
        if isinstance(message.channel, discord.DMChannel):
            if self.owner_id_config and message.author.id == self.owner_id_config:
                await self.process_commands(message)
                return
            
            # Check if this is part of an interview relay
            interview_cog = self.get_cog('Interview')
            if interview_cog:
                await interview_cog.handle_dm(message)
            return
        
        # Handle guild messages
        channel_id = message.channel.id
        
        # Check if we're active in this channel
        if channel_id not in self.active_sessions:
            return
        
        # Check if this is from the DM bot
        if self.dm_bot_id and message.author.id == self.dm_bot_id:
            gameplay_cog = self.get_cog('Gameplay')
            if gameplay_cog:
                await gameplay_cog.handle_dm_bot_message(message)
            return
        
        # Process commands if from owner
        if self.owner_id_config and message.author.id == self.owner_id_config:
            await self.process_commands(message)


# Create bot instance
bot = PartyMemberBot()


def run():
    """Run the bot"""
    bot.run(TOKEN)


if __name__ == "__main__":
    run()
