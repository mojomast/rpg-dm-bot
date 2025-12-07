"""
Party Member Bot - Gameplay Cog
Handles participating in game sessions and responding to the DM bot
"""

import discord
from discord.ext import commands
import logging
import asyncio
import random
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger('party_member.gameplay')


class Gameplay(commands.Cog):
    """Handles gameplay participation in RPG sessions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_responses: Dict[int, asyncio.Task] = {}  # channel_id -> response task
        self.last_message_time: Dict[int, datetime] = {}
        self.conversation_history: Dict[int, List[Dict]] = {}  # channel_id -> messages
        
    def get_character_context(self) -> str:
        """Build a context string about the character for response generation"""
        char = self.bot.character_data
        if not char:
            return "You are an adventurer."
        
        context = f"You are {char.get('name', 'an adventurer')}, "
        context += f"a Level {char.get('level', 1)} {char.get('race', '')} {char.get('class', '')}. "
        
        if char.get('personality'):
            context += f"Your personality: {char['personality']}. "
        
        if char.get('backstory'):
            context += f"Your backstory: {char['backstory'][:200]}. "
        
        play_style = char.get('play_style', 'balanced')
        style_descriptions = {
            'aggressive': "You tend to be bold and attack-first in combat.",
            'defensive': "You prefer to protect allies and avoid unnecessary risks.",
            'balanced': "You adapt your approach based on the situation.",
            'cautious': "You carefully consider options and avoid danger when possible.",
            'reckless': "You rush into action without much planning."
        }
        context += style_descriptions.get(play_style, "")
        
        return context
    
    async def handle_dm_bot_message(self, message: discord.Message):
        """Handle a message from the DM bot"""
        channel_id = message.channel.id
        
        # Store in conversation history
        if channel_id not in self.conversation_history:
            self.conversation_history[channel_id] = []
        
        self.conversation_history[channel_id].append({
            'author': 'dm',
            'content': message.content,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Keep only last 20 messages
        self.conversation_history[channel_id] = self.conversation_history[channel_id][-20:]
        
        # Check if we should respond
        if not self._should_respond(message):
            return
        
        # Check if auto-play is enabled for this channel
        if not self.bot.auto_play_mode.get(channel_id, False):
            logger.debug(f"Auto-play disabled for channel {channel_id}")
            return
        
        # Cancel any pending response for this channel
        if channel_id in self.pending_responses:
            self.pending_responses[channel_id].cancel()
        
        # Schedule a delayed response (to simulate reading/thinking time)
        delay = random.uniform(2.0, 6.0)
        self.pending_responses[channel_id] = asyncio.create_task(
            self._delayed_response(message, delay)
        )
    
    def _should_respond(self, message: discord.Message) -> bool:
        """Determine if the bot should respond to this message"""
        content = message.content.lower()
        char_name = self.bot.character_data.get('name', '').lower()
        
        # Check if bot is mentioned
        if self.bot.user.mentioned_in(message):
            return True
        
        # Check if character name is mentioned
        if char_name and char_name in content:
            return True
        
        # Check for question marks or prompts that suggest interaction needed
        question_indicators = ['?', 'what do you', 'what does', 'how do you', 'will you', 
                             'can you', 'do you', 'are you', 'your turn', 'your move']
        for indicator in question_indicators:
            if indicator in content:
                return True
        
        # Check for action prompts
        action_indicators = ['roll', 'attack', 'defend', 'cast', 'move', 'action', 
                            'initiative', 'combat', 'battle']
        for indicator in action_indicators:
            if indicator in content:
                return True
        
        return False
    
    async def _delayed_response(self, dm_message: discord.Message, delay: float):
        """Send a delayed response to simulate natural gameplay"""
        try:
            await asyncio.sleep(delay)
            
            # Show typing indicator
            async with dm_message.channel.typing():
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                # Generate and send response
                response = await self._generate_response(dm_message)
                if response:
                    await dm_message.channel.send(response)
                    
                    # Store our response in history
                    channel_id = dm_message.channel.id
                    self.conversation_history[channel_id].append({
                        'author': 'self',
                        'content': response,
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except asyncio.CancelledError:
            logger.debug("Response cancelled due to new message")
        except Exception as e:
            logger.error(f"Error generating response: {e}")
    
    async def _generate_response(self, dm_message: discord.Message) -> Optional[str]:
        """Generate a response based on the DM's message and character context"""
        char = self.bot.character_data
        if not char:
            return None
        
        content = dm_message.content.lower()
        char_name = char.get('name', 'Adventurer')
        char_class = char.get('class', 'Adventurer')
        play_style = char.get('play_style', 'balanced')
        
        # Handle different types of prompts
        
        # Combat/Action prompts
        if any(word in content for word in ['attack', 'combat', 'fight', 'battle', 'your turn']):
            return self._generate_combat_response(char_name, char_class, play_style)
        
        # Exploration prompts
        if any(word in content for word in ['look', 'search', 'examine', 'investigate']):
            return self._generate_exploration_response(char_name, play_style)
        
        # Social/dialogue prompts
        if any(word in content for word in ['speak', 'talk', 'ask', 'say', 'reply', 'respond']):
            return self._generate_social_response(char_name, char.get('personality', ''))
        
        # Choice prompts
        if 'choose' in content or 'option' in content or '?' in dm_message.content:
            return self._generate_choice_response(char_name, play_style, dm_message.content)
        
        # Default response
        return self._generate_generic_response(char_name, char_class)
    
    def _generate_combat_response(self, name: str, char_class: str, style: str) -> str:
        """Generate a combat-appropriate response"""
        class_actions = {
            'Warrior': ['attack with my sword', 'charge into battle', 'use my shield to defend'],
            'Mage': ['cast a spell', 'unleash magical energy', 'prepare an incantation'],
            'Rogue': ['strike from the shadows', 'look for a weak point', 'attempt a sneak attack'],
            'Cleric': ['call upon divine power', 'protect my allies', 'channel holy energy'],
            'Ranger': ['fire my bow', 'track the enemy', 'call upon nature'],
            'Bard': ['inspire my allies', 'weave a magical melody', 'taunt the enemy'],
            'Paladin': ['smite the enemy', 'defend the innocent', 'call upon sacred power'],
            'Warlock': ['invoke my patron', 'cast eldritch magic', 'channel dark power']
        }
        
        style_modifiers = {
            'aggressive': ["*charges forward* ", "*attacks fiercely* ", "*rushes in* "],
            'defensive': ["*carefully positions* ", "*guards allies* ", "*cautiously approaches* "],
            'balanced': ["*assesses the situation* ", "*readies for action* ", ""],
            'cautious': ["*waits for an opening* ", "*observes carefully* ", "*stays alert* "],
            'reckless': ["*without hesitation* ", "*throws caution to the wind* ", "*boldly* "]
        }
        
        actions = class_actions.get(char_class, ['prepare to fight', 'take action', 'ready myself'])
        modifiers = style_modifiers.get(style, [""])
        
        action = random.choice(actions)
        modifier = random.choice(modifiers)
        
        responses = [
            f"{modifier}{name} will {action}!",
            f"I {action}! {modifier.strip()}",
            f"{modifier}{name} shouts: \"For glory!\" and proceeds to {action}.",
            f"*{name} {action.replace('my', 'their')}*"
        ]
        
        return random.choice(responses)
    
    def _generate_exploration_response(self, name: str, style: str) -> str:
        """Generate an exploration response"""
        cautious_responses = [
            f"{name} carefully examines the surroundings.",
            f"*{name} looks around cautiously* I check for any dangers first.",
            f"I take my time to investigate thoroughly.",
        ]
        
        bold_responses = [
            f"{name} eagerly explores ahead!",
            f"*{name} rushes to investigate* What secrets await?",
            f"I search everywhere - leave no stone unturned!",
        ]
        
        if style in ['cautious', 'defensive']:
            return random.choice(cautious_responses)
        elif style in ['aggressive', 'reckless']:
            return random.choice(bold_responses)
        else:
            return random.choice(cautious_responses + bold_responses)
    
    def _generate_social_response(self, name: str, personality: str) -> str:
        """Generate a social/dialogue response"""
        responses = [
            f"*{name} steps forward* I'd like to speak.",
            f"{name} says: \"Greetings, I come in peace.\"",
            f"*{name} nods respectfully* Let me handle this.",
            f"I attempt to negotiate diplomatically.",
        ]
        
        if personality:
            if 'friendly' in personality.lower() or 'kind' in personality.lower():
                responses.append(f"*{name} smiles warmly* \"Well met, friend!\"")
            if 'gruff' in personality.lower() or 'stern' in personality.lower():
                responses.append(f"*{name} speaks bluntly* \"State your business.\"")
        
        return random.choice(responses)
    
    def _generate_choice_response(self, name: str, style: str, dm_content: str) -> str:
        """Generate a response to a choice prompt"""
        # Try to extract options from the message
        options = re.findall(r'(?:option\s*)?(\d+)[.):]\s*([^\n]+)', dm_content, re.IGNORECASE)
        
        if options:
            # Pick based on style
            if style == 'reckless':
                choice = options[-1]  # Most dramatic option usually last
            elif style == 'cautious':
                choice = options[0]  # Safest option usually first
            else:
                choice = random.choice(options)
            
            return f"{name} chooses option {choice[0]}: {choice[1].strip()[:50]}..."
        
        # Generic choice responses
        choice_num = random.randint(1, 3)
        return f"{name} chooses option {choice_num}."
    
    def _generate_generic_response(self, name: str, char_class: str) -> str:
        """Generate a generic response"""
        responses = [
            f"{name} is ready for whatever comes next!",
            f"*{name} nods* I'm with you.",
            f"Lead on! {name} follows.",
            f"*{name} prepares for adventure*",
            f"The {char_class} stands ready.",
        ]
        return random.choice(responses)
    
    async def send_character_message(self, channel: discord.TextChannel, message: str):
        """Send a message as the character"""
        char_name = self.bot.character_data.get('name', 'Adventurer')
        
        # Add some character flavor to the message
        formatted = f"**{char_name}**: {message}"
        
        async with channel.typing():
            await asyncio.sleep(random.uniform(0.5, 2.0))
            await channel.send(formatted)


async def setup(bot):
    await bot.add_cog(Gameplay(bot))
