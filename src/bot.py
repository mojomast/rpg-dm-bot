"""
RPG Dungeon Master Bot - Main Entry Point
An AI-powered Discord bot for running tabletop RPG games
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
import logging
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Generate log filename with timestamp
log_filename = f"logs/rpg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.getLogger().handlers[1].setLevel(logging.INFO)
logging.getLogger('aiosqlite').setLevel(logging.WARNING)
logging.getLogger('discord').setLevel(logging.INFO)

logger = logging.getLogger('rpg')
logger.info(f"Logging to file: {log_filename}")

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
REQUESTY_API_KEY = os.getenv('REQUESTY_API_KEY')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/rpg.db')
LLM_MODEL = os.getenv('LLM_MODEL', 'openai/gpt-4o-mini')

if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables!")

if not REQUESTY_API_KEY:
    logger.warning("REQUESTY_API_KEY not found - AI DM features will be disabled")
else:
    logger.info(f"LLM configured: {LLM_MODEL} via Requesty")


class RPGBot(commands.Bot):
    """The main RPG Dungeon Master bot class"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.db = None
        self.llm = None
        self._channel_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._started_at = None
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        # Initialize database
        from src.database import Database
        self.db = Database(DATABASE_PATH)
        await self.db.init()
        logger.info("Database initialized")
        
        # Initialize LLM client
        if REQUESTY_API_KEY:
            from src.llm import LLMClient
            self.llm = LLMClient(REQUESTY_API_KEY, LLM_MODEL)
            logger.info(f"LLM client initialized with model: {LLM_MODEL}")
        
        # Initialize prompts
        from src.prompts import Prompts
        self.prompts = Prompts()
        logger.info("Prompts loaded")
        
        # Initialize tool schemas
        from src.tool_schemas import ToolSchemas
        self.tool_schemas = ToolSchemas()
        logger.info("Tool schemas loaded")
        
        # Initialize tool executor
        from src.tools import ToolExecutor
        self.tools = ToolExecutor(self.db)
        logger.info("Tool executor initialized")
        
        # Load cogs
        cogs = [
            'src.cogs.characters',
            'src.cogs.combat',
            'src.cogs.inventory',
            'src.cogs.quests',
            'src.cogs.npcs',
            'src.cogs.dice',
            'src.cogs.sessions',
            'src.cogs.dm_chat',
            'src.cogs.game_master',
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        self._started_at = datetime.now(timezone.utc)
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Set presence
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="Dungeon Master | /help"
        )
        await self.change_presence(activity=activity)
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore messages from bots (including self)
        if message.author.bot:
            return
        
        # Ignore messages before bot was ready
        if self._started_at is None:
            return
        
        # Check if bot was mentioned
        if self.user in message.mentions:
            # Handle mention in chat cog
            chat_cog = self.get_cog('Chat')
            if chat_cog:
                async with self._channel_locks[message.channel.id]:
                    await chat_cog.handle_mention(message)
            return
        
        # Process commands
        await self.process_commands(message)
    
    async def close(self):
        """Clean up when bot shuts down"""
        if self.llm:
            await self.llm.close()
        await super().close()


# Create bot instance
bot = RPGBot()


# Global error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle application command errors"""
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ This command is on cooldown. Try again in {error.retry_after:.1f}s",
            ephemeral=True
        )
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True
        )
    else:
        logger.error(f"Command error: {error}", exc_info=True)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ An error occurred while processing this command.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ An error occurred while processing this command.",
                    ephemeral=True
                )
        except:
            pass


# Basic commands
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms")


@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    embed = discord.Embed(
        title="🎲 RPG Dungeon Master Bot",
        description=(
            "Your AI-powered Dungeon Master for tabletop RPG adventures!\n\n"
            "**🚀 Quick Start:** Use `/game menu` to get started!"
        ),
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🎮 Game Commands (`/game`)",
        value=(
            "`menu` - **Start here!** Main game menu\n"
            "`start` - Create a new game\n"
            "`join` - Join an existing game\n"
            "`begin` - Start the adventure\n"
            "`status` - Check game status"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🧙 Character Commands (`/character`)",
        value=(
            "`create` - Create a character\n"
            "`sheet` - View character sheet\n"
            "`levelup` - Level up\n"
            "`rest` - Rest to recover HP"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎭 Dungeon Master (`/dm`)",
        value=(
            "`/dm [message]` - Talk to the DM\n"
            "`/narrate` - Set a scene\n"
            "`/check` - Make a skill check\n"
            "Or @mention the bot in chat!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Combat (`/combat`)",
        value="`start` | `attack` | `defend` | `status`",
        inline=True
    )
    
    embed.add_field(
        name="🎒 Inventory (`/inventory`)",
        value="`view` | `use` | `equip` | `shop`",
        inline=True
    )
    
    embed.add_field(
        name="🎲 Dice (`/roll`)",
        value="`dice 2d6+3` | `attack` | `save`",
        inline=True
    )
    
    embed.set_footer(text="💡 Tip: Use /game menu for an interactive guide!")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="menu", description="Open the interactive game menu")
async def menu(interaction: discord.Interaction):
    """Show interactive menu - redirects to /game menu"""
    # Get the GameMaster cog
    game_master = bot.get_cog('GameMaster')
    if game_master:
        await game_master.game_menu(interaction)
    else:
        embed = discord.Embed(
            title="🎲 RPG Menu",
            description="Use `/game menu` for the full interactive menu!",
            color=discord.Color.purple()
        )
        view = MainMenuView()
        await interaction.response.send_message(embed=embed, view=view)


class MainMenuView(discord.ui.View):
    """Main menu with category buttons"""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="Character", emoji="🧙", style=discord.ButtonStyle.primary)
    async def character_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🧙 Character Menu",
            description="Manage your characters:",
            color=discord.Color.blue()
        )
        embed.add_field(name="/character create", value="Create a new character", inline=False)
        embed.add_field(name="/character sheet", value="View your character sheet", inline=False)
        embed.add_field(name="/character levelup", value="Level up your character", inline=False)
        embed.add_field(name="/character switch", value="Switch active character", inline=False)
        await interaction.response.edit_message(embed=embed)
    
    @discord.ui.button(label="Combat", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def combat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚔️ Combat Menu",
            description="Combat commands:",
            color=discord.Color.red()
        )
        embed.add_field(name="/combat start", value="Start a combat encounter", inline=False)
        embed.add_field(name="/combat attack", value="Attack a target", inline=False)
        embed.add_field(name="/combat defend", value="Take defensive stance", inline=False)
        embed.add_field(name="/combat status", value="View combat status", inline=False)
        await interaction.response.edit_message(embed=embed)
    
    @discord.ui.button(label="Inventory", emoji="🎒", style=discord.ButtonStyle.secondary)
    async def inventory_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎒 Inventory Menu",
            description="Manage your items:",
            color=discord.Color.green()
        )
        embed.add_field(name="/inventory view", value="View your inventory", inline=False)
        embed.add_field(name="/inventory use", value="Use an item", inline=False)
        embed.add_field(name="/inventory equip", value="Equip an item", inline=False)
        embed.add_field(name="/inventory shop", value="Visit a shop", inline=False)
        await interaction.response.edit_message(embed=embed)
    
    @discord.ui.button(label="Quests", emoji="📜", style=discord.ButtonStyle.success)
    async def quests_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📜 Quest Menu",
            description="Your adventures await:",
            color=discord.Color.gold()
        )
        embed.add_field(name="/quest list", value="View available quests", inline=False)
        embed.add_field(name="/quest info", value="Get quest details", inline=False)
        embed.add_field(name="/quest accept", value="Accept a quest", inline=False)
        await interaction.response.edit_message(embed=embed)
    
    @discord.ui.button(label="Roll Dice", emoji="🎲", style=discord.ButtonStyle.primary)
    async def dice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎲 Dice Menu",
            description="Roll the dice:",
            color=discord.Color.purple()
        )
        embed.add_field(name="/roll dice 1d20", value="Roll any dice", inline=False)
        embed.add_field(name="/roll attack", value="Roll an attack", inline=False)
        embed.add_field(name="/roll save", value="Roll a saving throw", inline=False)
        embed.add_field(name="/roll skill", value="Roll a skill check", inline=False)
        await interaction.response.edit_message(embed=embed)


def main():
    """Main entry point"""
    bot.run(TOKEN, log_handler=None)


if __name__ == '__main__':
    main()
