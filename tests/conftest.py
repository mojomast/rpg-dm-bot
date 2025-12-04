"""
Pytest fixtures for RPG DM Bot tests.
Provides in-memory database, mock LLM, and mock Discord context.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import tempfile
import os

from src.database import Database
from src.tools import DiceRoller, ToolExecutor


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def db():
    """Create a temporary database for testing"""
    # Use a temp file instead of :memory: because aiosqlite opens new connections
    # and :memory: databases are per-connection
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    database = Database(temp_db_path)
    await database.init()
    yield database
    
    # Cleanup
    try:
        os.unlink(temp_db_path)
    except:
        pass


@pytest_asyncio.fixture
async def db_with_character(db):
    """Database with a pre-created test character"""
    char_id = await db.create_character(
        user_id=12345,
        guild_id=67890,
        name="Test Hero",
        race="human",
        char_class="warrior",
        stats={
            "strength": 16,
            "dexterity": 14,
            "constitution": 15,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 8
        },
        backstory="A brave test warrior"
    )
    yield db, char_id


@pytest_asyncio.fixture
async def db_with_session(db):
    """Database with a pre-created test session"""
    session_id = await db.create_session(
        guild_id=67890,
        name="Test Campaign",
        dm_user_id=12345,
        description="A test adventure"
    )
    yield db, session_id


@pytest_asyncio.fixture
async def db_with_full_setup(db):
    """Database with character, session, quest, and NPC"""
    # Create session
    session_id = await db.create_session(
        guild_id=67890,
        name="Test Campaign",
        dm_user_id=12345,
        description="A test adventure"
    )
    
    # Create character
    char_id = await db.create_character(
        user_id=12345,
        guild_id=67890,
        name="Test Hero",
        race="human",
        char_class="warrior",
        stats={
            "strength": 16,
            "dexterity": 14,
            "constitution": 15,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 8
        },
        session_id=session_id
    )
    
    # Create NPC
    npc_id = await db.create_npc(
        guild_id=67890,
        name="Elara the Innkeeper",
        description="A friendly innkeeper",
        personality="Warm, welcoming, gossips about travelers",
        created_by=12345,
        npc_type="friendly",
        location="The Rusty Tankard Inn",
        session_id=session_id
    )
    
    # Create quest
    quest_id = await db.create_quest(
        guild_id=67890,
        title="The Missing Merchant",
        description="Find the missing merchant",
        objectives=[
            {"description": "Talk to the innkeeper", "completed": False},
            {"description": "Search the forest", "completed": False},
            {"description": "Rescue the merchant", "completed": False}
        ],
        rewards={"gold": 100, "xp": 50},
        created_by=12345,
        session_id=session_id,
        quest_giver_npc_id=npc_id
    )
    
    yield {
        "db": db,
        "session_id": session_id,
        "character_id": char_id,
        "npc_id": npc_id,
        "quest_id": quest_id,
        "user_id": 12345,
        "guild_id": 67890
    }


# =============================================================================
# DICE FIXTURES
# =============================================================================

@pytest.fixture
def dice_roller():
    """Create a DiceRoller instance"""
    return DiceRoller()


@pytest.fixture
def seeded_random():
    """Seed random for deterministic tests"""
    import random
    random.seed(42)
    yield
    random.seed()


# =============================================================================
# TOOL EXECUTOR FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def tool_executor(db):
    """Create a ToolExecutor with test database"""
    return ToolExecutor(db)


@pytest_asyncio.fixture
async def tool_executor_with_character(db_with_character):
    """ToolExecutor with a pre-created character"""
    db, char_id = db_with_character
    executor = ToolExecutor(db)
    yield executor, db, char_id


# =============================================================================
# CONTEXT FIXTURES
# =============================================================================

@pytest.fixture
def mock_context():
    """Create a mock Discord context"""
    return {
        "user_id": 12345,
        "guild_id": 67890,
        "channel_id": 11111,
        "session_id": None
    }


@pytest.fixture
def mock_context_with_session():
    """Create a mock Discord context with session"""
    return {
        "user_id": 12345,
        "guild_id": 67890,
        "channel_id": 11111,
        "session_id": 1
    }


# =============================================================================
# MOCK LLM FIXTURES
# =============================================================================

@pytest.fixture
def mock_llm_response():
    """Factory for creating mock LLM responses"""
    def _create_response(content: str = None, tool_calls: list = None):
        return {
            "content": content,
            "tool_calls": tool_calls or []
        }
    return _create_response


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    client = MagicMock()
    client.chat_with_tools = AsyncMock()
    client.dm_chat = AsyncMock()
    client.describe_scene = AsyncMock()
    return client


# =============================================================================
# DISCORD MOCK FIXTURES
# =============================================================================

@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction"""
    interaction = MagicMock()
    interaction.user = MagicMock()
    interaction.user.id = 12345
    interaction.user.name = "TestUser"
    interaction.guild = MagicMock()
    interaction.guild.id = 67890
    interaction.channel = MagicMock()
    interaction.channel.id = 11111
    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_message():
    """Create a mock Discord message"""
    message = MagicMock()
    message.author = MagicMock()
    message.author.id = 12345
    message.author.name = "TestUser"
    message.author.bot = False
    message.guild = MagicMock()
    message.guild.id = 67890
    message.channel = MagicMock()
    message.channel.id = 11111
    message.channel.send = AsyncMock()
    message.content = "Hello DM!"
    message.reply = AsyncMock()
    return message


# =============================================================================
# GAME DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_item():
    """Sample item data"""
    return {
        "id": "iron_sword",
        "name": "Iron Sword",
        "type": "weapon",
        "subtype": "sword",
        "damage": "1d8",
        "price": 50,
        "properties": {"slashing": True}
    }


@pytest.fixture
def sample_enemy():
    """Sample enemy data"""
    return {
        "id": "goblin",
        "name": "Goblin",
        "hp": 7,
        "ac": 15,
        "stats": {
            "strength": 8,
            "dexterity": 14,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 8,
            "charisma": 8
        },
        "attacks": [
            {"name": "Scimitar", "hit_bonus": 4, "damage": "1d6+2"}
        ],
        "xp_reward": 50
    }


@pytest.fixture
def sample_character_stats():
    """Sample character stats for creation"""
    return {
        "strength": 16,
        "dexterity": 14,
        "constitution": 15,
        "intelligence": 10,
        "wisdom": 12,
        "charisma": 8
    }
