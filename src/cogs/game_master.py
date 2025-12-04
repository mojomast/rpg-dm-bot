"""
RPG DM Bot - Game Master Cog
Handles game flow, session management, character interviews, and DM private messaging.
The session creator gets DM'd for meta/admin things.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import asyncio
import os

logger = logging.getLogger('rpg.game_master')


# Load starter kits data
def load_starter_kits():
    """Load starter kit definitions from JSON"""
    kit_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'game_data', 'starter_kits.json')
    try:
        with open(kit_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load starter kits: {e}")
        return {
            "starting_gold": 100,
            "class_kits": {},
            "shop_categories": {}
        }

STARTER_KITS = load_starter_kits()


# Required character fields for a complete character
REQUIRED_CHARACTER_FIELDS = {
    'name': 'What is your character\'s name?',
    'race': 'What race is your character? (Human, Elf, Dwarf, Halfling, Orc, Tiefling, Dragonborn, Gnome)',
    'char_class': 'What class is your character? (Warrior, Mage, Rogue, Cleric, Ranger, Bard, Paladin, Warlock)',
    'backstory': 'Tell me a bit about your character\'s backstory. Where did they come from? What drives them?',
}

# Fields that improve the game experience
OPTIONAL_CHARACTER_FIELDS = {
    'personality': 'How would you describe your character\'s personality in a few words?',
    'motivation': 'What is your character\'s primary motivation or goal?',
    'fear': 'What does your character fear most?',
    'bond': 'Who or what is most important to your character?',
}


# =============================================================================
# EQUIPMENT SHOP VIEWS
# =============================================================================

class EquipmentChoiceView(discord.ui.View):
    """Initial choice: Standard Kit or Custom Shopping"""
    
    def __init__(self, game_master_cog, user_id: int, guild_id: int, char_class: str):
        super().__init__(timeout=600)
        self.game_master = game_master_cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.char_class = char_class.lower()
        
    @discord.ui.button(label="⚔️ Take Standard Kit", style=discord.ButtonStyle.success, row=0)
    async def use_standard_kit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Use the pre-made class kit"""
        await interaction.response.defer()
        kit = STARTER_KITS.get('class_kits', {}).get(self.char_class)
        if kit:
            await self.game_master.assign_starter_kit(self.user_id, self.guild_id, self.char_class)
            
            # Show what they got
            items_text = "\n".join([f"• {item['name']}" + (f" x{item.get('quantity', 1)}" if item.get('quantity', 1) > 1 else "") 
                                    for item in kit['items']])
            
            embed = discord.Embed(
                title=f"🎒 {kit['name']} Equipped!",
                description=f"*{kit['description']}*\n\n**You received:**\n{items_text}\n\n💰 **Gold:** {kit['gold_remaining']}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
        else:
            # Fallback - just give gold
            await interaction.followup.send("⚠️ Kit not found for your class. You receive 50 gold to spend later!")
        
        # Continue interview
        await self.game_master.complete_character_interview(self.user_id)
        self.stop()
    
    @discord.ui.button(label="🛒 Shop for Equipment", style=discord.ButtonStyle.primary, row=0)
    async def custom_shopping(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open the equipment shop"""
        await interaction.response.defer()
        
        starting_gold = STARTER_KITS.get('starting_gold', 100)
        
        # Initialize shopping state
        self.game_master.active_interviews[self.user_id]['shopping'] = {
            'gold': starting_gold,
            'cart': [],
            'purchased': []
        }
        
        # Show shop interface
        await self.game_master.show_equipment_shop(
            interaction.channel,
            self.user_id,
            self.guild_id
        )
        self.stop()
    
    @discord.ui.button(label="📋 Preview Standard Kit", style=discord.ButtonStyle.secondary, row=1)
    async def preview_kit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Preview what's in the standard kit"""
        kit = STARTER_KITS.get('class_kits', {}).get(self.char_class)
        if kit:
            items_text = "\n".join([
                f"• **{item['name']}**" + (f" x{item.get('quantity', 1)}" if item.get('quantity', 1) > 1 else "") + 
                (" ✨ *equipped*" if item.get('equipped') else "")
                for item in kit['items']
            ])
            
            embed = discord.Embed(
                title=f"📋 {kit['name']} Preview",
                description=f"*{kit['description']}*\n\n**Contains:**\n{items_text}\n\n💰 **Starting Gold:** {kit['gold_remaining']}",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ No preview available for your class.", ephemeral=True)


class EquipmentShopView(discord.ui.View):
    """Main shop interface with category selection"""
    
    def __init__(self, game_master_cog, user_id: int, guild_id: int, gold: int):
        super().__init__(timeout=600)
        self.game_master = game_master_cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.gold = gold
        
        # Add category select dropdown
        self.add_item(ShopCategorySelect(game_master_cog, user_id, guild_id))
    
    @discord.ui.button(label="🛒 View Cart", style=discord.ButtonStyle.secondary, row=1)
    async def view_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current cart"""
        interview = self.game_master.active_interviews.get(self.user_id, {})
        shopping = interview.get('shopping', {})
        cart = shopping.get('cart', [])
        gold = shopping.get('gold', 0)
        
        if not cart:
            await interaction.response.send_message("🛒 Your cart is empty!", ephemeral=True)
            return
        
        cart_total = sum(item['price'] * item.get('quantity', 1) for item in cart)
        cart_text = "\n".join([
            f"• {item['name']} x{item.get('quantity', 1)} - {item['price'] * item.get('quantity', 1)}g"
            for item in cart
        ])
        
        embed = discord.Embed(
            title="🛒 Your Shopping Cart",
            description=f"{cart_text}\n\n**Total:** {cart_total}g\n💰 **Your Gold:** {gold}g",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="✅ Finish Shopping", style=discord.ButtonStyle.success, row=1)
    async def finish_shopping(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Complete the purchase and finish interview"""
        await interaction.response.defer()
        
        interview = self.game_master.active_interviews.get(self.user_id, {})
        shopping = interview.get('shopping', {})
        cart = shopping.get('cart', [])
        purchased = shopping.get('purchased', [])
        gold = shopping.get('gold', 0)
        
        # Process cart
        cart_total = sum(item['price'] * item.get('quantity', 1) for item in cart)
        if cart_total > gold:
            await interaction.followup.send("❌ You don't have enough gold for everything in your cart!", ephemeral=True)
            return
        
        # Finalize purchase
        final_gold = gold - cart_total
        all_items = purchased + cart
        
        # Assign all items and gold to character
        await self.game_master.complete_shopping(self.user_id, self.guild_id, all_items, final_gold)
        
        # Show summary
        if all_items:
            items_text = "\n".join([
                f"• {item['name']}" + (f" x{item.get('quantity', 1)}" if item.get('quantity', 1) > 1 else "")
                for item in all_items
            ])
            embed = discord.Embed(
                title="🎒 Shopping Complete!",
                description=f"**Your purchases:**\n{items_text}\n\n💰 **Remaining Gold:** {final_gold}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🎒 Shopping Complete!",
                description=f"You didn't buy anything.\n\n💰 **Gold:** {final_gold}",
                color=discord.Color.green()
            )
        
        await interaction.followup.send(embed=embed)
        
        # Complete character creation
        await self.game_master.complete_character_interview(self.user_id)
        self.stop()
    
    @discord.ui.button(label="❌ Clear Cart", style=discord.ButtonStyle.danger, row=1)
    async def clear_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Clear the shopping cart"""
        interview = self.game_master.active_interviews.get(self.user_id, {})
        shopping = interview.get('shopping', {})
        cart = shopping.get('cart', [])
        
        # Refund cart items
        cart_total = sum(item['price'] * item.get('quantity', 1) for item in cart)
        shopping['gold'] = shopping.get('gold', 0) + cart_total
        shopping['cart'] = []
        
        await interaction.response.send_message(
            f"🗑️ Cart cleared! Refunded {cart_total}g. You have {shopping['gold']}g.",
            ephemeral=True
        )


class ShopCategorySelect(discord.ui.Select):
    """Dropdown to select shop category"""
    
    def __init__(self, game_master_cog, user_id: int, guild_id: int):
        self.game_master = game_master_cog
        self.user_id = user_id
        self.guild_id = guild_id
        
        categories = STARTER_KITS.get('shop_categories', {})
        options = []
        for cat_id, cat_data in categories.items():
            options.append(discord.SelectOption(
                label=cat_data['name'],
                value=cat_id,
                emoji=cat_data.get('emoji', '📦'),
                description=f"Browse {cat_data['name'].lower()}"
            ))
        
        super().__init__(
            placeholder="🏪 Select a category to browse...",
            options=options if options else [discord.SelectOption(label="No categories", value="none")],
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        await self.game_master.show_category_items(
            interaction,
            self.user_id,
            self.guild_id,
            category
        )


class CategoryItemsView(discord.ui.View):
    """View items in a specific category"""
    
    def __init__(self, game_master_cog, user_id: int, guild_id: int, category: str, items: List[Dict]):
        super().__init__(timeout=600)
        self.game_master = game_master_cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.category = category
        self.items = items
        
        # Add item select dropdown
        self.add_item(ItemSelect(game_master_cog, user_id, guild_id, category, items))
    
    @discord.ui.button(label="⬅️ Back to Shop", style=discord.ButtonStyle.secondary, row=1)
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main shop"""
        await self.game_master.show_equipment_shop(
            interaction.channel,
            self.user_id,
            self.guild_id,
            edit_message=interaction.message
        )
        await interaction.response.defer()
        self.stop()


class ItemSelect(discord.ui.Select):
    """Dropdown to select and purchase items"""
    
    def __init__(self, game_master_cog, user_id: int, guild_id: int, category: str, items: List[Dict]):
        self.game_master = game_master_cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.category = category
        self.items_data = {item['id']: item for item in items}
        
        options = []
        for item in items[:25]:  # Discord limit
            price = item.get('price', 0)
            effect = item.get('effect', item.get('damage', item.get('ac', '')))
            options.append(discord.SelectOption(
                label=f"{item['name']} - {price}g",
                value=item['id'],
                description=str(effect)[:100] if effect else "Purchase this item"
            ))
        
        super().__init__(
            placeholder="🛍️ Select an item to buy...",
            options=options if options else [discord.SelectOption(label="No items", value="none")],
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        if item_id == "none":
            await interaction.response.send_message("No items available.", ephemeral=True)
            return
        
        item = self.items_data.get(item_id)
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return
        
        # Show purchase confirmation
        view = PurchaseConfirmView(self.game_master, self.user_id, self.guild_id, item, self.category)
        
        effect = item.get('effect', item.get('damage', item.get('ac', 'No special effect')))
        embed = discord.Embed(
            title=f"🛍️ {item['name']}",
            description=f"**Price:** {item['price']}g\n**Effect:** {effect}",
            color=discord.Color.gold()
        )
        
        interview = self.game_master.active_interviews.get(self.user_id, {})
        shopping = interview.get('shopping', {})
        gold = shopping.get('gold', 0)
        embed.set_footer(text=f"💰 Your gold: {gold}g")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PurchaseConfirmView(discord.ui.View):
    """Confirm item purchase with quantity selection"""
    
    def __init__(self, game_master_cog, user_id: int, guild_id: int, item: Dict, category: str):
        super().__init__(timeout=120)
        self.game_master = game_master_cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.item = item
        self.category = category
        self.quantity = 1
    
    @discord.ui.button(label="➖", style=discord.ButtonStyle.secondary, row=0)
    async def decrease_qty(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.quantity > 1:
            self.quantity -= 1
        await interaction.response.edit_message(
            content=f"**Quantity:** {self.quantity} (Total: {self.item['price'] * self.quantity}g)"
        )
    
    @discord.ui.button(label="➕", style=discord.ButtonStyle.secondary, row=0)
    async def increase_qty(self, interaction: discord.Interaction, button: discord.ui.Button):
        interview = self.game_master.active_interviews.get(self.user_id, {})
        shopping = interview.get('shopping', {})
        gold = shopping.get('gold', 0)
        
        max_qty = gold // self.item['price']
        if self.quantity < max_qty and self.quantity < 99:
            self.quantity += 1
        await interaction.response.edit_message(
            content=f"**Quantity:** {self.quantity} (Total: {self.item['price'] * self.quantity}g)"
        )
    
    @discord.ui.button(label="Buy 1", style=discord.ButtonStyle.success, row=0, custom_id="buy_one")
    async def buy_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.purchase(interaction, 1)
    
    @discord.ui.button(label="Buy Selected Qty", style=discord.ButtonStyle.success, row=1)
    async def buy_quantity(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.purchase(interaction, self.quantity)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Purchase cancelled.", view=None, embed=None)
        self.stop()
    
    async def purchase(self, interaction: discord.Interaction, quantity: int):
        interview = self.game_master.active_interviews.get(self.user_id, {})
        shopping = interview.get('shopping', {})
        gold = shopping.get('gold', 0)
        
        total_cost = self.item['price'] * quantity
        
        if total_cost > gold:
            await interaction.response.edit_message(
                content=f"❌ Not enough gold! You need {total_cost}g but only have {gold}g.",
                view=None, embed=None
            )
            return
        
        # Deduct gold and add to cart
        shopping['gold'] = gold - total_cost
        shopping['cart'].append({
            'id': self.item['id'],
            'name': self.item['name'],
            'type': self.category,
            'price': self.item['price'],
            'quantity': quantity
        })
        
        await interaction.response.edit_message(
            content=f"✅ Added **{self.item['name']}** x{quantity} to cart! (-{total_cost}g)\n💰 Remaining: {shopping['gold']}g",
            view=None, embed=None
        )
        self.stop()


class CharacterInterviewView(discord.ui.View):
    """View for character interview with quick response options"""
    
    def __init__(self, game_master_cog, user_id: int, guild_id: int, field: str):
        super().__init__(timeout=600)
        self.game_master = game_master_cog
        self.user_id = user_id
        self.guild_id = guild_id
        self.field = field
        
        # Add quick options for race/class selection
        if field == 'race':
            self.add_race_buttons()
        elif field == 'char_class':
            self.add_class_buttons()
    
    def add_race_buttons(self):
        races = ['Human', 'Elf', 'Dwarf', 'Halfling', 'Orc', 'Tiefling', 'Dragonborn', 'Gnome']
        for i, race in enumerate(races[:4]):
            btn = discord.ui.Button(label=race, style=discord.ButtonStyle.primary, row=0)
            btn.callback = self.make_race_callback(race)
            self.add_item(btn)
        for i, race in enumerate(races[4:]):
            btn = discord.ui.Button(label=race, style=discord.ButtonStyle.primary, row=1)
            btn.callback = self.make_race_callback(race)
            self.add_item(btn)
    
    def add_class_buttons(self):
        classes = ['Warrior', 'Mage', 'Rogue', 'Cleric', 'Ranger', 'Bard', 'Paladin', 'Warlock']
        for i, char_class in enumerate(classes[:4]):
            btn = discord.ui.Button(label=char_class, style=discord.ButtonStyle.success, row=0)
            btn.callback = self.make_class_callback(char_class)
            self.add_item(btn)
        for i, char_class in enumerate(classes[4:]):
            btn = discord.ui.Button(label=char_class, style=discord.ButtonStyle.success, row=1)
            btn.callback = self.make_class_callback(char_class)
            self.add_item(btn)
    
    def make_race_callback(self, race: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            await self.game_master.process_interview_response(
                interaction.user.id, 
                self.guild_id, 
                'race', 
                race,
                interaction.channel
            )
        return callback
    
    def make_class_callback(self, char_class: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            await self.game_master.process_interview_response(
                interaction.user.id, 
                self.guild_id, 
                'char_class', 
                char_class,
                interaction.channel
            )
        return callback


class QuickStartView(discord.ui.View):
    """View for quick game start options"""
    
    def __init__(self, game_master_cog):
        super().__init__(timeout=300)
        self.game_master = game_master_cog
    
    @discord.ui.button(label="🎮 Start New Game", style=discord.ButtonStyle.success, row=0)
    async def start_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start a new game session"""
        modal = QuickStartModal(self.game_master)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="👤 Create Character", style=discord.ButtonStyle.primary, row=0)
    async def create_character(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start character creation"""
        # Start the interview process
        await interaction.response.defer(ephemeral=True)
        await self.game_master.start_character_interview(interaction.user, interaction.guild)
        await interaction.followup.send(
            "✨ Check your DMs! The Dungeon Master will help you create your character.",
            ephemeral=True
        )
    
    @discord.ui.button(label="📋 Join Existing Game", style=discord.ButtonStyle.secondary, row=0)
    async def join_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show available games to join"""
        sessions = await self.game_master.bot.db.get_sessions(interaction.guild.id, status='active')
        
        if not sessions:
            sessions = await self.game_master.bot.db.get_sessions(interaction.guild.id, status='inactive')
        
        if not sessions:
            await interaction.response.send_message(
                "❌ No games available to join. Start a new one with the button above!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎲 Available Games",
            description="Click a button to join a game:",
            color=discord.Color.blue()
        )
        
        view = GameListView(self.game_master, sessions[:5])  # Show up to 5
        
        for session in sessions[:5]:
            dm = interaction.guild.get_member(session['dm_user_id'])
            dm_name = dm.display_name if dm else "Unknown"
            players = await self.game_master.bot.db.get_session_players(session['id'])
            
            status_emoji = "🟢" if session['status'] == 'active' else "🟡"
            embed.add_field(
                name=f"{status_emoji} {session['name']}",
                value=f"DM: {dm_name}\nPlayers: {len(players)}/{session['max_players']}\n`/game join {session['id']}`",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="❓ How to Play", style=discord.ButtonStyle.secondary, row=1)
    async def how_to_play(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show how to play guide"""
        embed = discord.Embed(
            title="📖 How to Play",
            description="Welcome to the AI Dungeon Master RPG!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="1️⃣ Create a Character",
            value="Use `/character create` or click the button above. The DM will interview you to build your character!",
            inline=False
        )
        
        embed.add_field(
            name="2️⃣ Join or Start a Game",
            value="Start a new game with `/game start` or join an existing one with `/game join`",
            inline=False
        )
        
        embed.add_field(
            name="3️⃣ Play the Game",
            value="@mention the bot or use `/dm` to talk to the Dungeon Master. Describe what you want to do!",
            inline=False
        )
        
        embed.add_field(
            name="4️⃣ Rolling Dice",
            value="Use `/roll dice 1d20` or let the DM roll for you when you take actions",
            inline=False
        )
        
        embed.add_field(
            name="💡 Tips",
            value="• Be creative with your actions!\n• The DM responds to roleplay\n• Explore, fight, talk to NPCs\n• Your choices matter!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class QuickStartModal(discord.ui.Modal, title="Start New Game"):
    """Modal for quickly starting a new game"""
    
    game_name = discord.ui.TextInput(
        label="Game Name",
        placeholder="The Dragon's Lair",
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label="Brief Description (optional)",
        style=discord.TextStyle.paragraph,
        placeholder="A mysterious dungeon has appeared near the village...",
        max_length=300,
        required=False
    )
    
    def __init__(self, game_master_cog):
        super().__init__()
        self.game_master = game_master_cog
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Create the session
        session_id = await self.game_master.bot.db.create_session(
            guild_id=interaction.guild.id,
            name=str(self.game_name),
            description=str(self.description) if self.description.value else "A new adventure awaits!",
            dm_user_id=interaction.user.id,
            max_players=6
        )
        
        # Get or create character for the game creator
        char = await self.game_master.bot.db.get_active_character(
            interaction.user.id, 
            interaction.guild.id
        )
        
        # Send DM to session creator about game management
        try:
            dm_channel = await interaction.user.create_dm()
            
            admin_embed = discord.Embed(
                title="🎭 You're Now the Dungeon Master!",
                description=f"You've created **{self.game_name}**. Here are your admin controls:",
                color=discord.Color.purple()
            )
            
            admin_embed.add_field(
                name="🎮 Game Commands",
                value=(
                    f"`/game begin {session_id}` - Start the adventure\n"
                    f"`/game pause {session_id}` - Pause the game\n"
                    f"`/game end {session_id}` - End the session\n"
                    f"`/game status {session_id}` - Check game status"
                ),
                inline=False
            )
            
            admin_embed.add_field(
                name="📢 Announcements",
                value="I'll DM you privately for meta things like:\n• Player issues\n• Story planning suggestions\n• Game management alerts",
                inline=False
            )
            
            admin_embed.add_field(
                name="💡 Tips",
                value="• Let the AI DM run the story\n• You can guide it with `/dm` commands\n• Use `/narrate` to set scenes\n• The AI remembers the story!",
                inline=False
            )
            
            await dm_channel.send(embed=admin_embed)
            
        except discord.Forbidden:
            logger.warning(f"Could not DM user {interaction.user.id}")
        
        # Handle character situation
        if not char:
            # No character - start interview
            embed = discord.Embed(
                title=f"🎲 Game Created: {self.game_name}",
                description=(
                    "Your game is ready! But you need a character to play.\n\n"
                    "**Check your DMs** - The Dungeon Master will help you create one!"
                ),
                color=discord.Color.green()
            )
            embed.add_field(name="Session ID", value=str(session_id), inline=True)
            embed.add_field(name="Players", value="Waiting for characters...", inline=True)
            
            await interaction.followup.send(embed=embed)
            await self.game_master.start_character_interview(interaction.user, interaction.guild)
            
        else:
            # Has character - add to session and offer to start
            await self.game_master.bot.db.add_session_player(session_id, char['id'])
            
            embed = discord.Embed(
                title=f"🎲 Game Created: {self.game_name}",
                description=f"**{char['name']}** is ready to adventure!",
                color=discord.Color.green()
            )
            embed.add_field(name="Session ID", value=str(session_id), inline=True)
            embed.add_field(name="Your Character", value=f"{char['name']} the {char['race']} {char['char_class']}", inline=True)
            embed.add_field(
                name="Next Steps",
                value=f"• Share the session ID for others to join\n• Use `/game begin {session_id}` when ready to start!",
                inline=False
            )
            
            view = BeginGameView(self.game_master, session_id)
            await interaction.followup.send(embed=embed, view=view)


class BeginGameView(discord.ui.View):
    """View to begin the game"""
    
    def __init__(self, game_master_cog, session_id: int):
        super().__init__(timeout=600)
        self.game_master = game_master_cog
        self.session_id = session_id
    
    @discord.ui.button(label="⚔️ Begin Adventure!", style=discord.ButtonStyle.success)
    async def begin_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Begin the game"""
        await self.game_master.begin_game(interaction, self.session_id)
        self.stop()
    
    @discord.ui.button(label="⏳ Wait for More Players", style=discord.ButtonStyle.secondary)
    async def wait_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Just acknowledge waiting"""
        await interaction.response.send_message(
            f"👍 Take your time! Use `/game begin {self.session_id}` when everyone's ready.",
            ephemeral=True
        )


class SessionSelectView(discord.ui.View):
    """View for selecting which session to manage/play"""
    
    def __init__(self, game_master_cog, sessions: List[Dict], action: str = "play"):
        super().__init__(timeout=300)
        self.game_master = game_master_cog
        self.sessions = sessions
        self.action = action
        
        # Add session select dropdown if there are sessions
        if sessions:
            self.add_item(SessionSelectDropdown(game_master_cog, sessions, action))
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, row=1)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the session list"""
        sessions = await self.game_master.bot.db.get_sessions(interaction.guild.id)
        
        embed = discord.Embed(
            title="🎲 Available Games",
            description="Select a game to play or manage:",
            color=discord.Color.blue()
        )
        
        if not sessions:
            embed.description = "No games found! Create one with the button below."
        else:
            for s in sessions[:10]:
                status_emoji = {"active": "🟢", "paused": "🟡", "inactive": "⚪", "completed": "✅"}.get(s['status'], "⚪")
                players = await self.game_master.bot.db.get_session_players(s['id'])
                embed.add_field(
                    name=f"{status_emoji} {s['name']} `ID: {s['id']}`",
                    value=f"Players: {len(players)}/{s['max_players']} | Status: {s['status']}",
                    inline=True
                )
        
        new_view = SessionSelectView(self.game_master, sessions, self.action)
        await interaction.response.edit_message(embed=embed, view=new_view)
    
    @discord.ui.button(label="➕ Create New Game", style=discord.ButtonStyle.success, row=1)
    async def create_new(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a new game session"""
        modal = QuickStartModal(self.game_master)
        await interaction.response.send_modal(modal)


class SessionSelectDropdown(discord.ui.Select):
    """Dropdown for selecting a session"""
    
    def __init__(self, game_master_cog, sessions: List[Dict], action: str):
        self.game_master = game_master_cog
        self.action = action
        self.sessions_map = {str(s['id']): s for s in sessions}
        
        options = []
        for s in sessions[:25]:  # Discord limit
            status_emoji = {"active": "🟢", "paused": "🟡", "inactive": "⚪"}.get(s['status'], "⚪")
            options.append(discord.SelectOption(
                label=f"{s['name'][:50]}",
                value=str(s['id']),
                description=f"ID: {s['id']} | Status: {s['status']}",
                emoji=status_emoji
            ))
        
        super().__init__(
            placeholder="🎮 Select a game...",
            options=options if options else [discord.SelectOption(label="No games", value="none")],
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        session_id = self.values[0]
        if session_id == "none":
            await interaction.response.send_message("No games available!", ephemeral=True)
            return
        
        session = self.sessions_map.get(session_id)
        if not session:
            await interaction.response.send_message("Session not found!", ephemeral=True)
            return
        
        # Show session management view
        view = SessionManageView(self.game_master, session)
        
        players = await self.game_master.bot.db.get_session_players(session['id'])
        player_list = ""
        for p in players:
            # Skip players without a character assigned
            if not p.get('character_id'):
                continue
            char = await self.game_master.bot.db.get_character(p['character_id'])
            if char:
                player_list += f"• **{char['name']}** - Lvl {char['level']} {char['race']} {char['char_class']}\n"
        
        embed = discord.Embed(
            title=f"🎲 {session['name']}",
            description=session.get('description', 'No description'),
            color=discord.Color.gold()
        )
        embed.add_field(name="Session ID", value=f"`{session['id']}`", inline=True)
        embed.add_field(name="Status", value=session['status'].title(), inline=True)
        embed.add_field(name="Players", value=f"{len(players)}/{session['max_players']}", inline=True)
        
        if player_list:
            embed.add_field(name="Party", value=player_list, inline=False)
        else:
            embed.add_field(name="Party", value="*No players yet*", inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class SessionManageView(discord.ui.View):
    """View for managing a specific session"""
    
    def __init__(self, game_master_cog, session: Dict):
        super().__init__(timeout=300)
        self.game_master = game_master_cog
        self.session = session
    
    @discord.ui.button(label="▶️ Begin/Resume", style=discord.ButtonStyle.success, row=0)
    async def begin_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Begin or resume the game"""
        await self.game_master.begin_game(interaction, self.session['id'])
    
    @discord.ui.button(label="🚪 Join Game", style=discord.ButtonStyle.primary, row=0)
    async def join_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Join this game session"""
        char = await self.game_master.bot.db.get_active_character(
            interaction.user.id, interaction.guild.id
        )
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first! Use `/character create`",
                ephemeral=True
            )
            return
        
        # Check if already in session
        players = await self.game_master.bot.db.get_session_players(self.session['id'])
        if any(p.get('character_id') == char['id'] for p in players if p.get('character_id')):
            await interaction.response.send_message(
                f"✅ **{char['name']}** is already in this game!",
                ephemeral=True
            )
            return
        
        await self.game_master.bot.db.add_session_player(self.session['id'], char['id'])
        await interaction.response.send_message(
            f"✅ **{char['name']}** has joined **{self.session['name']}**! 🎉"
        )
    
    @discord.ui.button(label="👋 Leave Game", style=discord.ButtonStyle.danger, row=0)
    async def leave_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Leave this game session"""
        char = await self.game_master.bot.db.get_active_character(
            interaction.user.id, interaction.guild.id
        )
        
        if not char:
            await interaction.response.send_message("❌ You don't have a character!", ephemeral=True)
            return
        
        await self.game_master.bot.db.remove_session_player(self.session['id'], char['id'])
        await interaction.response.send_message(
            f"👋 **{char['name']}** has left **{self.session['name']}**.",
            ephemeral=True
        )
    
    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary, row=1)
    async def pause_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pause the game"""
        if self.session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the game creator can pause!",
                ephemeral=True
            )
            return
        
        await self.game_master.bot.db.update_session(self.session['id'], status='paused')
        await interaction.response.send_message(
            f"⏸️ **{self.session['name']}** has been paused."
        )
    
    @discord.ui.button(label="🔄 Reset History", style=discord.ButtonStyle.secondary, row=1)
    async def reset_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset the DM's conversation history for this game"""
        dm_chat_cog = self.game_master.bot.get_cog('DMChat')
        if dm_chat_cog:
            dm_chat_cog.start_new_session(interaction.channel.id, self.session['id'])
        
        await interaction.response.send_message(
            f"🔄 Conversation history cleared for **{self.session['name']}**!\n"
            "The DM will start fresh while keeping all game data.",
            ephemeral=True
        )


class GameListView(discord.ui.View):
    """View for listing and joining games"""
    
    def __init__(self, game_master_cog, sessions: List[Dict]):
        super().__init__(timeout=300)
        self.game_master = game_master_cog
        
        # Add join buttons for each session
        for i, session in enumerate(sessions[:5]):
            btn = discord.ui.Button(
                label=f"Join: {session['name'][:20]}",
                style=discord.ButtonStyle.success,
                custom_id=f"join_{session['id']}",
                row=i
            )
            btn.callback = self.make_join_callback(session['id'], session['name'])
            self.add_item(btn)
    
    def make_join_callback(self, session_id: int, session_name: str):
        async def callback(interaction: discord.Interaction):
            char = await self.game_master.bot.db.get_active_character(
                interaction.user.id,
                interaction.guild.id
            )
            
            if not char:
                await interaction.response.send_message(
                    "❌ You need a character first! Click 'Create Character' or use `/character create`",
                    ephemeral=True
                )
                return
            
            await self.game_master.bot.db.add_session_player(session_id, char['id'])
            
            await interaction.response.send_message(
                f"✅ **{char['name']}** has joined **{session_name}**! 🎉",
                ephemeral=False
            )
        return callback


class GameMaster(commands.Cog):
    """Main game master functionality - interviews, game flow, DM messaging"""
    
    def __init__(self, bot):
        self.bot = bot
        # Track ongoing character interviews {user_id: interview_state}
        self.active_interviews: Dict[int, Dict[str, Any]] = {}
        # Track active games {session_id: game_state}
        self.active_games: Dict[int, Dict[str, Any]] = {}
    
    @property
    def db(self):
        return self.bot.db
    
    @property
    def llm(self):
        return self.bot.llm
    
    def _generate_fallback_intro(self, session: Dict, party_info: List[Dict]) -> str:
        """Generate a fallback intro when LLM fails or returns empty"""
        party_text = "\n".join([
            f"• **{c['name']}** - Level {c['level']} {c['race']} {c.get('char_class', 'Adventurer')}"
            for c in party_info
        ])
        
        return (
            f"*The mists part to reveal your party standing at the crossroads of fate...*\n\n"
            f"**Welcome, brave adventurers, to {session['name']}!**\n\n"
            f"{session.get('description') or 'Your journey begins here.'}\n\n"
            f"**Your Party:**\n{party_text}\n\n"
            f"*The adventure awaits. What would you like to do?*"
        )
    
    # =========================================================================
    # GAME COMMANDS
    # =========================================================================
    
    game_group = app_commands.Group(
        name="game", 
        description="Game management commands",
        guild_only=True
    )
    
    @game_group.command(name="menu", description="Open the game menu - start here!")
    async def game_menu(self, interaction: discord.Interaction):
        """Show the main game menu"""
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command must be used in a server, not in DMs!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎲 RPG Dungeon Master",
            description=(
                "**Welcome, adventurer!**\n\n"
                "Ready to embark on an AI-powered tabletop RPG adventure? "
                "The Dungeon Master awaits to guide you through dangerous dungeons, "
                "mysterious quests, and epic battles!\n\n"
                "**Choose an option below to get started:**"
            ),
            color=discord.Color.gold()
        )
        
        # Check if user has a character
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if char:
            embed.add_field(
                name="👤 Your Character",
                value=f"**{char['name']}** - Level {char['level']} {char['race']} {char['char_class']}\n❤️ {char['hp']}/{char['max_hp']} HP",
                inline=False
            )
        else:
            embed.add_field(
                name="👤 No Character Yet!",
                value="Create one to start playing!",
                inline=False
            )
        
        # Check for active sessions
        sessions = await self.db.get_sessions(interaction.guild.id, status='active')
        if sessions:
            session_list = "\n".join([f"• **{s['name']}** (ID: {s['id']})" for s in sessions[:3]])
            embed.add_field(
                name="🎮 Active Games",
                value=session_list,
                inline=False
            )
        
        view = QuickStartView(self)
        await interaction.response.send_message(embed=embed, view=view)
    
    @game_group.command(name="start", description="Start a new game session")
    @app_commands.describe(
        name="Name for your game session",
        description="Brief description of the adventure"
    )
    async def start_game(
        self,
        interaction: discord.Interaction,
        name: str,
        description: Optional[str] = None
    ):
        """Create and optionally start a new game"""
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command must be used in a server, not in DMs!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Create session
        session_id = await self.db.create_session(
            guild_id=interaction.guild.id,
            name=name,
            description=description or "A new adventure awaits!",
            dm_user_id=interaction.user.id,
            max_players=6
        )
        
        # Get user's character
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        # DM the session creator
        try:
            dm_channel = await interaction.user.create_dm()
            admin_embed = discord.Embed(
                title="🎭 Game Master Controls",
                description=f"You're running **{name}** (Session #{session_id})",
                color=discord.Color.purple()
            )
            admin_embed.add_field(
                name="Commands",
                value=(
                    f"`/game begin {session_id}` - Start the adventure\n"
                    f"`/game status {session_id}` - View game status\n"
                    f"`/game pause {session_id}` - Pause game\n"
                    f"`/game end {session_id}` - End session"
                ),
                inline=False
            )
            await dm_channel.send(embed=admin_embed)
        except discord.Forbidden:
            pass
        
        if not char:
            embed = discord.Embed(
                title=f"🎲 Game Created: {name}",
                description="You need a character to play! Check your DMs for character creation.",
                color=discord.Color.yellow()
            )
            embed.add_field(name="Session ID", value=str(session_id), inline=True)
            await interaction.followup.send(embed=embed)
            await self.start_character_interview(interaction.user, interaction.guild)
        else:
            await self.db.add_session_player(session_id, char['id'])
            embed = discord.Embed(
                title=f"🎲 Game Created: {name}",
                description=f"**{char['name']}** is ready to adventure!",
                color=discord.Color.green()
            )
            embed.add_field(name="Session ID", value=str(session_id), inline=True)
            embed.add_field(
                name="Next Steps",
                value=f"• Others join with `/game join {session_id}`\n• Begin with `/game begin {session_id}`",
                inline=False
            )
            view = BeginGameView(self, session_id)
            await interaction.followup.send(embed=embed, view=view)
    
    @game_group.command(name="join", description="Join an existing game session")
    @app_commands.describe(session_id="The session ID to join")
    async def join_game(self, interaction: discord.Interaction, session_id: int):
        """Join a game session"""
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command must be used in a server, not in DMs!",
                ephemeral=True
            )
            return
        
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You need a character first! Use `/game menu` to create one.",
                ephemeral=True
            )
            return
        
        # Check if already in session
        players = await self.db.get_session_players(session_id)
        if any(p.get('character_id') == char['id'] for p in players if p.get('character_id')):
            await interaction.response.send_message(
                f"You're already in **{session['name']}**!",
                ephemeral=True
            )
            return
        
        # Check capacity
        if len(players) >= session['max_players']:
            await interaction.response.send_message("❌ This game is full!", ephemeral=True)
            return
        
        await self.db.add_session_player(session_id, char['id'])
        
        await interaction.response.send_message(
            f"✅ **{char['name']}** has joined **{session['name']}**! 🎉\n"
            f"Party size: {len(players) + 1}/{session['max_players']}"
        )
        
        # Notify the DM
        try:
            dm_user = interaction.guild.get_member(session['dm_user_id'])
            if dm_user:
                dm_channel = await dm_user.create_dm()
                await dm_channel.send(
                    f"🎮 **{char['name']}** ({interaction.user.display_name}) has joined your game **{session['name']}**!"
                )
        except discord.Forbidden:
            pass
    
    @game_group.command(name="list", description="Browse and manage available games")
    async def list_games(self, interaction: discord.Interaction):
        """Show all games with an interactive menu"""
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command must be used in a server, not in DMs!",
                ephemeral=True
            )
            return
        
        sessions = await self.db.get_sessions(interaction.guild.id)
        
        embed = discord.Embed(
            title="🎲 Available Games",
            description="Select a game to view details and manage:",
            color=discord.Color.blue()
        )
        
        if not sessions:
            embed.description = "No games found! Create one with the button below."
        else:
            for s in sessions[:10]:
                status_emoji = {"active": "🟢", "paused": "🟡", "inactive": "⚪", "completed": "✅"}.get(s['status'], "⚪")
                players = await self.db.get_session_players(s['id'])
                embed.add_field(
                    name=f"{status_emoji} {s['name']} `ID: {s['id']}`",
                    value=f"Players: {len(players)}/{s['max_players']} | Status: {s['status']}",
                    inline=True
                )
        
        view = SessionSelectView(self, sessions)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @game_group.command(name="begin", description="Begin the adventure! (Game creator only)")
    @app_commands.describe(session_id="The session ID to begin")
    async def begin_game_cmd(self, interaction: discord.Interaction, session_id: int):
        """Begin a game session"""
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command must be used in a server, not in DMs!",
                ephemeral=True
            )
            return
        
        await self.begin_game(interaction, session_id)
    
    async def begin_game(self, interaction: discord.Interaction, session_id: int):
        """Actually begin the game with DM narration"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        
        if session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the game creator can begin the adventure!",
                ephemeral=True
            )
            return
        
        players = await self.db.get_session_players(session_id)
        
        if not players:
            await interaction.response.send_message(
                "❌ No players have joined yet! Wait for players or create a character first.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Mark session as active
        await self.db.update_session(session_id, status='active')
        
        # Clear chat history for this channel to start fresh with new game
        dm_chat_cog = self.bot.get_cog('DMChat')
        if dm_chat_cog:
            dm_chat_cog.start_new_session(interaction.channel.id, session_id)
        
        # Build detailed party info for the DM including backstories
        party_info = []
        for p in players:
            # Skip players without a character assigned
            if not p.get('character_id'):
                continue
            char = await self.db.get_character(p['character_id'])
            if char:
                party_info.append(char)
        
        # Build party text with backstories
        party_lines = []
        for c in party_info:
            char_line = f"• **{c['name']}** - Level {c['level']} {c['race']} {c['char_class']}"
            party_lines.append(char_line)
            if c.get('backstory'):
                party_lines.append(f"  *Backstory:* {c['backstory']}")
        party_text = "\n".join(party_lines)
        
        # Get the AI DM to introduce the adventure
        if self.llm:
            # Use the game_start_prompt which includes full party details
            intro_prompt = self.bot.prompts.get_game_start_prompt(
                session_name=session['name'],
                session_description=session['description'] or 'An epic adventure awaits!',
                party=party_info
            )
            
            logger.info(f"Starting game '{session['name']}' with {len(party_info)} players")
            logger.info(f"Game description: {session['description']}")
            
            try:
                response = await self.llm.chat(
                    messages=[
                        {"role": "system", "content": intro_prompt},
                        {"role": "user", "content": "Begin our adventure!"}
                    ],
                    max_tokens=15000
                )
                
                # llm.chat() returns a string directly
                dm_intro = response if isinstance(response, str) else response.get('content', '')
                
                # Handle empty response (some models return reasoning tokens but no content)
                if not dm_intro or not dm_intro.strip():
                    logger.warning("LLM returned empty response, using fallback intro")
                    dm_intro = self._generate_fallback_intro(session, party_info)
                else:
                    logger.info(f"DM intro generated: {dm_intro[:200]}...")
            except Exception as e:
                logger.error(f"Error getting DM intro: {e}", exc_info=True)
                dm_intro = self._generate_fallback_intro(session, party_info)
        else:
            dm_intro = (
                f"⚔️ **{session['name']}** has begun!\n\n"
                f"{session['description'] or 'Your adventure awaits!'}\n\n"
                f"**Party:**\n{party_text}\n\n"
                "@mention me to interact with the Dungeon Master!"
            )
        
        # Create announcement embed
        embed = discord.Embed(
            title=f"⚔️ {session['name']} Begins!",
            description=dm_intro,
            color=discord.Color.gold()
        )
        embed.set_footer(text="@mention the bot or use /dm to interact with the Dungeon Master!")
        
        await interaction.followup.send(embed=embed)
        
        # Store active game state with full session info
        self.active_games[session_id] = {
            'session': session,
            'party': party_info,
            'started_at': datetime.utcnow().isoformat(),
            'turn_count': 0,
            'game_name': session['name'],
            'game_description': session['description']
        }
        
        # Save game state to database for persistence
        await self.db.save_game_state(
            session_id=session_id,
            current_scene="Opening Scene",
            current_location="Starting Location",
            dm_notes=f"Adventure '{session['name']}' has begun. {session['description']}",
            game_data={
                'party_info': [{'name': c['name'], 'race': c['race'], 'char_class': c['char_class'], 
                               'level': c['level'], 'backstory': c.get('backstory')} for c in party_info],
                'session_name': session['name'],
                'session_description': session['description']
            }
        )
        
        # DM the session creator
        try:
            dm_user = interaction.guild.get_member(session['dm_user_id'])
            if dm_user:
                dm_channel = await dm_user.create_dm()
                await dm_channel.send(
                    f"🎮 **{session['name']}** is now live!\n\n"
                    f"The AI DM will keep things moving. Use `/dm` or `/narrate` to guide the story.\n"
                    f"Use `/game pause {session_id}` if you need a break!"
                )
        except discord.Forbidden:
            pass
    
    @game_group.command(name="status", description="Check game status")
    @app_commands.describe(session_id="The session ID to check (optional)")
    async def game_status(self, interaction: discord.Interaction, session_id: Optional[int] = None):
        """Check game status"""
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command must be used in a server, not in DMs!",
                ephemeral=True
            )
            return
        
        if session_id:
            session = await self.db.get_session(session_id)
            if not session:
                await interaction.response.send_message("❌ Game not found!", ephemeral=True)
                return
            sessions = [session]
        else:
            # Get all active sessions in guild
            sessions = await self.db.get_sessions(interaction.guild.id, status='active')
            if not sessions:
                sessions = await self.db.get_sessions(interaction.guild.id, status='inactive')
        
        if not sessions:
            await interaction.response.send_message(
                "No games found! Start one with `/game start`",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎲 Game Status",
            color=discord.Color.blue()
        )
        
        for session in sessions[:5]:
            players = await self.db.get_session_players(session['id'])
            dm = interaction.guild.get_member(session['dm_user_id'])
            
            status_emoji = {"active": "🟢", "paused": "🟡", "inactive": "⚪", "completed": "✅"}.get(session['status'], "⚪")
            
            player_names = []
            for p in players:
                # Skip players without a character assigned
                if not p.get('character_id'):
                    continue
                char = await self.db.get_character(p['character_id'])
                if char:
                    player_names.append(f"{char['name']} (Lv.{char['level']})")
            
            embed.add_field(
                name=f"{status_emoji} {session['name']} (ID: {session['id']})",
                value=(
                    f"**Status:** {session['status'].title()}\n"
                    f"**DM:** {dm.display_name if dm else 'Unknown'}\n"
                    f"**Players:** {', '.join(player_names) or 'None'}\n"
                    f"**Capacity:** {len(players)}/{session['max_players']}"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @game_group.command(name="pause", description="Pause the current game (creator only)")
    @app_commands.describe(session_id="The session ID to pause")
    async def pause_game(self, interaction: discord.Interaction, session_id: int):
        """Pause a game"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        
        if session['dm_user_id'] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the game creator can pause the game!",
                ephemeral=True
            )
            return
        
        await self.db.update_session(session_id, status='paused')
        
        await interaction.response.send_message(
            f"⏸️ **{session['name']}** has been paused.\n"
            f"Use `/game begin {session_id}` to resume!"
        )
    
    @game_group.command(name="end", description="End the current game (creator only)")
    @app_commands.describe(session_id="The session ID to end")
    async def end_game(self, interaction: discord.Interaction, session_id: int):
        """End a game"""
        session = await self.db.get_session(session_id)
        
        if not session:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        
        if session['dm_user_id'] != interaction.user.id:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Only the game creator or an admin can end the game!",
                    ephemeral=True
                )
                return
        
        await self.db.update_session(session_id, status='completed')
        
        # Clean up active game state
        if session_id in self.active_games:
            del self.active_games[session_id]
        
        embed = discord.Embed(
            title=f"🏁 {session['name']} Has Ended",
            description="Thank you for playing! The adventure has concluded.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="What's Next?",
            value="Start a new adventure with `/game start`!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    # =========================================================================
    # CHARACTER INTERVIEW SYSTEM
    # =========================================================================
    
    async def start_character_interview(self, user: discord.User, guild: discord.Guild):
        """Start the character creation interview via DM"""
        try:
            dm_channel = await user.create_dm()
        except discord.Forbidden:
            logger.warning(f"Cannot DM user {user.id}")
            return
        
        # Initialize interview state
        self.active_interviews[user.id] = {
            'guild_id': guild.id,
            'dm_channel': dm_channel,
            'current_field': None,
            'responses': {},
            'stage': 'greeting'
        }
        
        # Send greeting
        embed = discord.Embed(
            title="🎭 Character Creation Interview",
            description=(
                f"Greetings, adventurer! I am the Dungeon Master for **{guild.name}**.\n\n"
                "I'll help you create your character through a brief interview. "
                "Just answer my questions naturally - you can type your responses or use the buttons when available.\n\n"
                "Let's begin!"
            ),
            color=discord.Color.purple()
        )
        
        await dm_channel.send(embed=embed)
        
        # Ask first question
        await asyncio.sleep(1)  # Brief pause for readability
        await self.ask_next_interview_question(user.id)
    
    async def ask_next_interview_question(self, user_id: int):
        """Ask the next question in the interview"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        dm_channel = interview['dm_channel']
        responses = interview['responses']
        
        # Determine next field to ask about
        next_field = None
        for field in ['name', 'race', 'char_class', 'backstory']:
            if field not in responses:
                next_field = field
                break
        
        if next_field is None:
            # All basic questions answered - move to equipment phase
            await self.start_equipment_phase(user_id)
            return
        
        interview['current_field'] = next_field
        question = REQUIRED_CHARACTER_FIELDS[next_field]
        
        # Create view with buttons for race/class
        view = None
        if next_field in ['race', 'char_class']:
            view = CharacterInterviewView(self, user_id, interview['guild_id'], next_field)
        
        # Use AI to make the question more engaging if available
        if self.llm and next_field == 'backstory':
            char_name = responses.get('name', 'adventurer')
            char_race = responses.get('race', 'unknown')
            char_class = responses.get('char_class', 'unknown')
            
            question = (
                f"Excellent choice! So **{char_name}**, a {char_race} {char_class}...\n\n"
                f"Every hero has a story. What's yours?\n\n"
                f"*Tell me about {char_name}'s past - where they came from, what shaped them, "
                f"or what drove them to become an adventurer. A few sentences is perfect!*"
            )
        
        embed = discord.Embed(
            title=f"📝 Character Creation ({list(REQUIRED_CHARACTER_FIELDS.keys()).index(next_field) + 1}/5)",
            description=question,
            color=discord.Color.blue()
        )
        
        if view:
            await dm_channel.send(embed=embed, view=view)
        else:
            await dm_channel.send(embed=embed)
    
    async def start_equipment_phase(self, user_id: int):
        """Start the equipment selection phase of character creation"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        dm_channel = interview['dm_channel']
        responses = interview['responses']
        char_class = responses.get('char_class', 'warrior').lower()
        
        # Mark that we're now in equipment phase
        interview['current_field'] = 'equipment'
        interview['stage'] = 'equipment'
        
        # Get class kit info
        kit = STARTER_KITS.get('class_kits', {}).get(char_class)
        starting_gold = STARTER_KITS.get('starting_gold', 100)
        
        kit_preview = ""
        if kit:
            kit_preview = f"\n\n**📋 Your {kit['name']}:**\n*{kit['description']}*"
        
        embed = discord.Embed(
            title="⚔️ Equipment Selection (5/5)",
            description=(
                f"Every adventurer needs proper gear, **{responses.get('name', 'hero')}**!\n\n"
                f"You have **{starting_gold} gold** to spend on equipment.\n\n"
                f"You can either:\n"
                f"🎒 **Take the Standard {char_class.title()} Kit** - A curated set of gear perfect for your class\n"
                f"🛒 **Shop for Equipment** - Hand-pick your own weapons, armor, and supplies"
                f"{kit_preview}"
            ),
            color=discord.Color.gold()
        )
        
        view = EquipmentChoiceView(self, user_id, interview['guild_id'], char_class)
        await dm_channel.send(embed=embed, view=view)
    
    async def show_equipment_shop(self, channel, user_id: int, guild_id: int, edit_message=None):
        """Display the main equipment shop interface"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        shopping = interview.get('shopping', {'gold': 100, 'cart': [], 'purchased': []})
        gold = shopping.get('gold', 100)
        
        embed = discord.Embed(
            title="🏪 The Adventurer's Outfitter",
            description=(
                "*A weathered shopkeeper grins at you from behind piles of equipment*\n\n"
                f"\"Welcome, adventurer! Browse my wares and outfit yourself for glory!\"\n\n"
                f"💰 **Your Gold:** {gold}g\n"
                f"🛒 **Cart Items:** {len(shopping.get('cart', []))}"
            ),
            color=discord.Color.blue()
        )
        
        # Add category previews
        categories = STARTER_KITS.get('shop_categories', {})
        for cat_id, cat_data in list(categories.items())[:4]:
            items = cat_data.get('items', [])
            item_range = f"{min(i['price'] for i in items)}g - {max(i['price'] for i in items)}g" if items else "N/A"
            embed.add_field(
                name=f"{cat_data['emoji']} {cat_data['name']}",
                value=f"{len(items)} items ({item_range})",
                inline=True
            )
        
        view = EquipmentShopView(self, user_id, guild_id, gold)
        
        if edit_message:
            await edit_message.edit(embed=embed, view=view)
        else:
            await channel.send(embed=embed, view=view)
    
    async def show_category_items(self, interaction: discord.Interaction, user_id: int, guild_id: int, category: str):
        """Show items in a specific category"""
        categories = STARTER_KITS.get('shop_categories', {})
        cat_data = categories.get(category, {})
        items = cat_data.get('items', [])
        
        if not items:
            await interaction.response.send_message("No items in this category!", ephemeral=True)
            return
        
        interview = self.active_interviews.get(user_id, {})
        shopping = interview.get('shopping', {})
        gold = shopping.get('gold', 0)
        
        # Build item list
        items_text = "\n".join([
            f"**{item['name']}** - {item['price']}g\n"
            f"   ↳ {item.get('effect', item.get('damage', item.get('ac', 'No special effect')))}"
            for item in items
        ])
        
        embed = discord.Embed(
            title=f"{cat_data.get('emoji', '📦')} {cat_data['name']}",
            description=f"💰 **Your Gold:** {gold}g\n\n{items_text}",
            color=discord.Color.blue()
        )
        
        view = CategoryItemsView(self, user_id, guild_id, category, items)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def assign_starter_kit(self, user_id: int, guild_id: int, char_class: str):
        """Assign the standard starter kit to a character"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        kit = STARTER_KITS.get('class_kits', {}).get(char_class.lower())
        
        if not kit:
            return
        
        # Store kit items and gold for when character is created
        interview['equipment'] = {
            'items': kit['items'],
            'gold': kit['gold_remaining']
        }
    
    async def complete_shopping(self, user_id: int, guild_id: int, items: List[Dict], gold: int):
        """Complete shopping and store purchased items"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        
        # Store purchased items for when character is created
        interview['equipment'] = {
            'items': items,
            'gold': gold
        }
    
    async def process_interview_response(
        self,
        user_id: int,
        guild_id: int,
        field: str,
        value: str,
        channel: discord.abc.Messageable = None
    ):
        """Process a response to an interview question"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        
        # Validate and store response
        interview['responses'][field] = value
        
        # Send acknowledgment
        dm_channel = channel or interview['dm_channel']
        
        acknowledgments = {
            'name': f"**{value}** - a fine name for a hero!",
            'race': f"A **{value}**! An excellent choice.",
            'char_class': f"The path of the **{value}** - adventurous!",
            'backstory': "A compelling story! The threads of fate weave together..."
        }
        
        await dm_channel.send(acknowledgments.get(field, "Noted!"))
        await asyncio.sleep(0.5)
        
        # Ask next question
        await self.ask_next_interview_question(user_id)
    
    async def complete_character_interview(self, user_id: int):
        """Complete the interview and create the character"""
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        responses = interview['responses']
        dm_channel = interview['dm_channel']
        guild_id = interview['guild_id']
        equipment_data = interview.get('equipment', {})
        
        # Generate stats (use standard array with some randomness)
        import random
        base_stats = [15, 14, 13, 12, 10, 8]
        random.shuffle(base_stats)
        
        stats = {
            'strength': base_stats[0],
            'dexterity': base_stats[1],
            'constitution': base_stats[2],
            'intelligence': base_stats[3],
            'wisdom': base_stats[4],
            'charisma': base_stats[5]
        }
        
        # Create character
        char_id = await self.db.create_character(
            user_id=user_id,
            guild_id=guild_id,
            name=responses['name'],
            race=responses['race'],
            char_class=responses['char_class'],
            stats=stats,
            backstory=responses.get('backstory')
        )
        
        char = await self.db.get_character(char_id)
        
        # Add equipment items to inventory
        equipment_items = equipment_data.get('items', [])
        starting_gold = equipment_data.get('gold', 50)  # Default to 50 gold if not set
        
        for item in equipment_items:
            quantity = item.get('quantity', 1)
            should_equip = item.get('equipped', False)
            properties = {}
            if item.get('effect'):
                properties['effect'] = item['effect']
            if item.get('damage'):
                properties['damage'] = item['damage']
            if item.get('ac'):
                properties['ac'] = item['ac']
            
            await self.db.add_item(
                character_id=char_id,
                item_id=item['id'],
                item_name=item['name'],
                item_type=item.get('type', 'misc'),
                quantity=quantity,
                properties=properties if properties else None,
                is_equipped=should_equip,
                slot=item.get('slot')
            )
        
        # Add starting gold
        await self.db.add_item(
            character_id=char_id,
            item_id='gold',
            item_name='Gold',
            item_type='currency',
            quantity=starting_gold
        )
        
        # Initialize spells and abilities for spellcasting classes
        await self._initialize_character_spells(char_id, char['char_class'], char['level'])
        
        # Build inventory text - get from database since items are now stored
        equipped_items = await self.db.get_equipped_items(char_id)
        all_inventory = await self.db.get_inventory(char_id)
        other_items = [i for i in all_inventory if not i['is_equipped'] and i['item_type'] != 'currency']
        
        inventory_text = ""
        if equipped_items:
            inventory_text += "**⚔️ Equipped:**\n"
            inventory_text += "\n".join([f"• {i['item_name']}" for i in equipped_items[:5]])
            if len(equipped_items) > 5:
                inventory_text += f"\n...and {len(equipped_items) - 5} more"
        
        if other_items:
            inventory_text += "\n\n**🎒 Inventory:**\n"
            inventory_text += "\n".join([
                f"• {i['item_name']}" + (f" x{i['quantity']}" if i.get('quantity', 1) > 1 else "")
                for i in other_items[:5]
            ])
            if len(other_items) > 5:
                inventory_text += f"\n...and {len(other_items) - 5} more"
        
        # Get spell info for display
        spells = await self.db.get_character_spells(char_id)
        spell_text = ""
        if spells:
            cantrips = [s for s in spells if s['is_cantrip']]
            leveled = [s for s in spells if not s['is_cantrip']]
            if cantrips:
                spell_text = f"**✨ Cantrips:** {', '.join([s['spell_name'] for s in cantrips[:4]])}"
            if leveled:
                spell_text += f"\n**📖 Spells:** {', '.join([s['spell_name'] for s in leveled[:4]])}"
        
        # Send completion message
        embed = discord.Embed(
            title="🎉 Character Created!",
            description=f"Welcome to the world, **{char['name']}**!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Your Character",
            value=(
                f"**Name:** {char['name']}\n"
                f"**Race:** {char['race']}\n"
                f"**Class:** {char['char_class']}\n"
                f"**Level:** {char['level']}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="📈 Stats",
            value=(
                f"STR: {char['strength']} | DEX: {char['dexterity']}\n"
                f"CON: {char['constitution']} | INT: {char['intelligence']}\n"
                f"WIS: {char['wisdom']} | CHA: {char['charisma']}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="❤️ Health & Gold",
            value=f"{char['hp']}/{char['max_hp']} HP\n💰 {starting_gold} Gold",
            inline=True
        )
        
        if inventory_text:
            embed.add_field(
                name="🎒 Equipment",
                value=inventory_text,
                inline=False
            )
        
        if spell_text:
            embed.add_field(
                name="🔮 Spells",
                value=spell_text,
                inline=False
            )
        
        if char['backstory']:
            embed.add_field(
                name="📜 Backstory",
                value=char['backstory'][:200] + ("..." if len(char['backstory']) > 200 else ""),
                inline=False
            )
        
        embed.add_field(
            name="🎮 Next Steps",
            value=(
                "Return to the server and:\n"
                "• Join a game with `/game join [id]`\n"
                "• Start your own with `/game start`\n"
                "• View your sheet with `/character sheet`\n"
                "• Check inventory with `/inventory`"
            ),
            inline=False
        )
        
        await dm_channel.send(embed=embed)
        
        # Clean up interview state
        del self.active_interviews[user_id]
    
    async def _initialize_character_spells(self, char_id: int, char_class: str, level: int):
        """Initialize starting spells and spell slots for a character"""
        import json
        import os
        
        # Load spells data
        spells_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'game_data', 'spells.json')
        try:
            with open(spells_file, 'r', encoding='utf-8') as f:
                spells_data = json.load(f)
        except FileNotFoundError:
            return
        
        char_class_lower = char_class.lower()
        class_spells = spells_data.get('class_spell_lists', {}).get(char_class_lower)
        
        if not class_spells:
            return  # Non-spellcasting class
        
        all_spells = spells_data.get('spells', {})
        
        # Learn starting cantrips (usually 2-3)
        cantrip_ids = class_spells.get('cantrips', [])
        cantrips_to_learn = cantrip_ids[:3]  # Start with 3 cantrips
        
        for spell_id in cantrips_to_learn:
            spell = all_spells.get(spell_id)
            if spell:
                await self.db.learn_spell(
                    character_id=char_id,
                    spell_id=spell_id,
                    spell_name=spell['name'],
                    spell_level=0,
                    is_cantrip=True,
                    source='class'
                )
        
        # Learn starting level 1 spells (usually 2-4)
        level1_ids = class_spells.get('1', [])
        spells_to_learn = level1_ids[:4]  # Start with 4 level 1 spells
        
        for spell_id in spells_to_learn:
            spell = all_spells.get(spell_id)
            if spell:
                await self.db.learn_spell(
                    character_id=char_id,
                    spell_id=spell_id,
                    spell_name=spell['name'],
                    spell_level=spell['level'],
                    is_cantrip=False,
                    source='class'
                )
        
        # Load class data for spell slots
        classes_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'game_data', 'classes.json')
        try:
            with open(classes_file, 'r', encoding='utf-8') as f:
                classes_data = json.load(f)
        except FileNotFoundError:
            return
        
        class_info = classes_data.get('classes', {}).get(char_class_lower, {})
        spell_slots = class_info.get('spell_slots', {})
        
        # Get spell slots for current level
        for str_level, slots in spell_slots.items():
            if int(str_level) <= level:
                # slots is an array like [2] for level 1, [4, 2] for level 3, etc.
                slot_dict = {}
                for slot_level, count in enumerate(slots, 1):
                    if count > 0:
                        slot_dict[slot_level] = count
                
                if slot_dict:
                    await self.db.set_spell_slots(char_id, slot_dict)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for DM responses during character interview"""
        # Ignore bots
        if message.author.bot:
            return
        
        # Only process DMs
        if message.guild is not None:
            return
        
        # Check if user is in an interview
        user_id = message.author.id
        if user_id not in self.active_interviews:
            return
        
        interview = self.active_interviews[user_id]
        current_field = interview.get('current_field')
        
        if not current_field:
            return
        
        # Process the response
        await self.process_interview_response(
            user_id,
            interview['guild_id'],
            current_field,
            message.content,
            message.channel
        )
    
    # =========================================================================
    # DM NOTIFICATIONS (Meta/Admin Messages)
    # =========================================================================
    
    async def notify_game_creator(
        self,
        session_id: int,
        title: str,
        message: str,
        color: discord.Color = discord.Color.blue()
    ):
        """Send a notification to the game creator via DM"""
        session = await self.db.get_session(session_id)
        if not session:
            return
        
        try:
            # We need to get the user from any guild they share with the bot
            user = self.bot.get_user(session['dm_user_id'])
            if not user:
                user = await self.bot.fetch_user(session['dm_user_id'])
            
            dm_channel = await user.create_dm()
            
            embed = discord.Embed(
                title=f"🎭 {title}",
                description=f"**Game:** {session['name']}\n\n{message}",
                color=color
            )
            
            await dm_channel.send(embed=embed)
            
        except (discord.Forbidden, discord.NotFound):
            logger.warning(f"Could not notify game creator {session['dm_user_id']}")
    
    async def check_party_status(self, session_id: int) -> Dict[str, Any]:
        """Check the party status and identify any issues"""
        session = await self.db.get_session(session_id)
        if not session:
            return {'error': 'Session not found'}
        
        players = await self.db.get_session_players(session_id)
        
        issues = []
        warnings = []
        
        party_data = []
        for p in players:
            # Skip players without a character assigned
            if not p.get('character_id'):
                continue
            char = await self.db.get_character(p['character_id'])
            if char:
                party_data.append(char)
                
                # Check for issues
                if char['hp'] <= 0:
                    issues.append(f"**{char['name']}** is unconscious/dead!")
                elif char['hp'] < char['max_hp'] * 0.25:
                    warnings.append(f"**{char['name']}** is critically wounded ({char['hp']}/{char['max_hp']} HP)")
        
        return {
            'party': party_data,
            'issues': issues,
            'warnings': warnings,
            'player_count': len(players),
            'max_players': session['max_players']
        }


async def setup(bot):
    await bot.add_cog(GameMaster(bot))
