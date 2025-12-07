"""
Party Member Bot - Configuration Management
Handles loading, saving, and managing bot configuration
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

logger = logging.getLogger('party_member.config')


@dataclass
class CharacterConfig:
    """Stores character information"""
    name: str = "Unnamed Adventurer"
    race: str = ""
    char_class: str = ""
    level: int = 1
    backstory: str = ""
    personality: str = ""
    
    # Stats
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    # Character ID from the DM bot (once registered)
    dm_bot_character_id: Optional[int] = None
    
    # Behavior settings
    play_style: str = "balanced"  # aggressive, defensive, balanced, cautious, reckless
    verbosity: str = "normal"  # quiet, normal, verbose
    
    # Creation tracking
    creation_complete: bool = False
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass  
class BotConfig:
    """Stores bot-wide configuration"""
    owner_id: Optional[int] = None
    dm_bot_id: Optional[int] = None
    
    # Channels the bot is active in
    active_channels: list = field(default_factory=list)
    
    # Auto-play settings
    auto_play_enabled: bool = False
    auto_play_delay_min: float = 2.0  # Min seconds before responding
    auto_play_delay_max: float = 8.0  # Max seconds before responding
    
    # Response behavior
    respond_to_dm_bot: bool = True  # Respond when DM bot asks something
    respond_to_mentions: bool = True  # Respond when mentioned
    
    # Guilds this bot is registered in
    registered_guilds: list = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ConfigManager:
    """Manages all configuration for the party member bot"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.character_file = os.path.join(data_dir, "character.json")
        self.config_file = os.path.join(data_dir, "config.json")
        
        self.character = CharacterConfig()
        self.bot_config = BotConfig()
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
    
    def load(self) -> None:
        """Load all configuration from files"""
        self._load_character()
        self._load_bot_config()
    
    def save(self) -> None:
        """Save all configuration to files"""
        self._save_character()
        self._save_bot_config()
    
    def _load_character(self) -> None:
        """Load character configuration"""
        if os.path.exists(self.character_file):
            try:
                with open(self.character_file, 'r') as f:
                    data = json.load(f)
                self.character = CharacterConfig.from_dict(data)
                logger.info(f"Loaded character: {self.character.name}")
            except Exception as e:
                logger.error(f"Failed to load character config: {e}")
                self.character = CharacterConfig()
        else:
            logger.info("No character config found, using defaults")
    
    def _save_character(self) -> None:
        """Save character configuration"""
        try:
            with open(self.character_file, 'w') as f:
                json.dump(self.character.to_dict(), f, indent=2)
            logger.info(f"Saved character: {self.character.name}")
        except Exception as e:
            logger.error(f"Failed to save character config: {e}")
    
    def _load_bot_config(self) -> None:
        """Load bot configuration"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                self.bot_config = BotConfig.from_dict(data)
                logger.info("Loaded bot config")
            except Exception as e:
                logger.error(f"Failed to load bot config: {e}")
                self.bot_config = BotConfig()
        else:
            logger.info("No bot config found, using defaults")
    
    def _save_bot_config(self) -> None:
        """Save bot configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.bot_config.to_dict(), f, indent=2)
            logger.info("Saved bot config")
        except Exception as e:
            logger.error(f"Failed to save bot config: {e}")
    
    def update_character(self, **kwargs) -> None:
        """Update character fields and save"""
        for key, value in kwargs.items():
            if hasattr(self.character, key):
                setattr(self.character, key, value)
        self._save_character()
    
    def update_bot_config(self, **kwargs) -> None:
        """Update bot config fields and save"""
        for key, value in kwargs.items():
            if hasattr(self.bot_config, key):
                setattr(self.bot_config, key, value)
        self._save_bot_config()
    
    def add_active_channel(self, channel_id: int) -> None:
        """Add a channel to active channels"""
        if channel_id not in self.bot_config.active_channels:
            self.bot_config.active_channels.append(channel_id)
            self._save_bot_config()
    
    def remove_active_channel(self, channel_id: int) -> None:
        """Remove a channel from active channels"""
        if channel_id in self.bot_config.active_channels:
            self.bot_config.active_channels.remove(channel_id)
            self._save_bot_config()
    
    def is_channel_active(self, channel_id: int) -> bool:
        """Check if a channel is active"""
        return channel_id in self.bot_config.active_channels
