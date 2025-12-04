"""
RPG DM Bot - Inventory Cog
Handles item management, equipment, and shops
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger('rpg.inventory')

# Equipment slots
EQUIPMENT_SLOTS = ["weapon", "armor", "helmet", "shield", "boots", "accessory"]

# Sample shop items
SHOP_ITEMS = [
    {"id": "potion_health", "name": "Health Potion", "type": "consumable", "price": 50,
     "properties": {"heal": 10}, "description": "Restores 10 HP"},
    {"id": "potion_mana", "name": "Mana Potion", "type": "consumable", "price": 50,
     "properties": {"mana": 10}, "description": "Restores 10 Mana"},
    {"id": "sword_iron", "name": "Iron Sword", "type": "weapon", "price": 100,
     "properties": {"damage": "1d8", "bonus_attack": 1}, "description": "+1 to attack, 1d8 damage"},
    {"id": "shield_wooden", "name": "Wooden Shield", "type": "shield", "price": 75,
     "properties": {"bonus_ac": 2}, "description": "+2 AC"},
    {"id": "armor_leather", "name": "Leather Armor", "type": "armor", "price": 150,
     "properties": {"bonus_ac": 3}, "description": "+3 AC"},
    {"id": "torch", "name": "Torch", "type": "misc", "price": 5,
     "properties": {"light": True}, "description": "Provides light in dark places"},
    {"id": "rope", "name": "Rope (50ft)", "type": "misc", "price": 10,
     "properties": {"length": 50}, "description": "Useful for climbing and tying things"},
]


class ShopView(discord.ui.View):
    """View for browsing and purchasing shop items"""
    
    def __init__(self, bot, character_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.character_id = character_id
        self.page = 0
        self.items_per_page = 5
    
    def get_page_items(self):
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        return SHOP_ITEMS[start:end]
    
    async def update_embed(self, interaction: discord.Interaction):
        char = await self.bot.db.get_character(self.character_id)
        items = self.get_page_items()
        
        embed = discord.Embed(
            title="🛒 General Store",
            description=f"Your gold: **{char['gold']}** 💰\n\nSelect an item to purchase:",
            color=discord.Color.gold()
        )
        
        for item in items:
            embed.add_field(
                name=f"{item['name']} - {item['price']} gold",
                value=item['description'],
                inline=False
            )
        
        total_pages = (len(SHOP_ITEMS) + self.items_per_page - 1) // self.items_per_page
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages}")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self.update_embed(interaction)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_pages = (len(SHOP_ITEMS) + self.items_per_page - 1) // self.items_per_page
        if self.page < total_pages - 1:
            self.page += 1
        await self.update_embed(interaction)
    
    @discord.ui.select(
        placeholder="Select an item to buy...",
        options=[
            discord.SelectOption(label=item['name'], value=item['id'], description=f"{item['price']} gold")
            for item in SHOP_ITEMS[:25]
        ]
    )
    async def buy_item(self, interaction: discord.Interaction, select: discord.ui.Select):
        item_id = select.values[0]
        item = next((i for i in SHOP_ITEMS if i['id'] == item_id), None)
        
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return
        
        char = await self.bot.db.get_character(self.character_id)
        
        if char['gold'] < item['price']:
            await interaction.response.send_message(
                f"❌ Not enough gold! You have {char['gold']}, need {item['price']}.",
                ephemeral=True
            )
            return
        
        # Purchase item
        await self.bot.db.update_gold(self.character_id, -item['price'])
        await self.bot.db.add_item(
            self.character_id, item['id'], item['name'],
            item['type'], 1, item.get('properties', {})
        )
        
        await interaction.response.send_message(
            f"✅ Purchased **{item['name']}** for {item['price']} gold!",
            ephemeral=True
        )


class Inventory(commands.Cog):
    """Inventory management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    inventory_group = app_commands.Group(name="inventory", description="Inventory commands")
    
    @inventory_group.command(name="view", description="View your inventory")
    async def view_inventory(self, interaction: discord.Interaction):
        """Display inventory contents"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        items = await self.db.get_inventory(char['id'])
        
        embed = discord.Embed(
            title=f"🎒 {char['name']}'s Inventory",
            description=f"💰 Gold: **{char['gold']}**",
            color=discord.Color.blue()
        )
        
        if not items:
            embed.add_field(name="Items", value="Your inventory is empty!", inline=False)
        else:
            # Group by type
            by_type = {}
            for item in items:
                item_type = item['item_type']
                if item_type not in by_type:
                    by_type[item_type] = []
                by_type[item_type].append(item)
            
            for item_type, type_items in by_type.items():
                lines = []
                for item in type_items:
                    equipped = "⚔️ " if item['is_equipped'] else ""
                    qty = f" x{item['quantity']}" if item['quantity'] > 1 else ""
                    lines.append(f"{equipped}[{item['id']}] {item['item_name']}{qty}")
                
                embed.add_field(
                    name=f"{item_type.title()}s",
                    value="\n".join(lines) or "None",
                    inline=True
                )
        
        await interaction.response.send_message(embed=embed)
    
    @inventory_group.command(name="use", description="Use a consumable item")
    @app_commands.describe(item_id="The inventory ID of the item to use")
    async def use_item(self, interaction: discord.Interaction, item_id: int):
        """Use a consumable item"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        items = await self.db.get_inventory(char['id'])
        item = next((i for i in items if i['id'] == item_id), None)
        
        if not item:
            await interaction.response.send_message(
                "❌ Item not found in your inventory!",
                ephemeral=True
            )
            return
        
        if item['item_type'] != 'consumable':
            await interaction.response.send_message(
                "❌ This item cannot be used! Try equipping it instead.",
                ephemeral=True
            )
            return
        
        # Apply item effects
        props = item['properties']
        effects = []
        
        if 'heal' in props:
            new_hp = min(char['max_hp'], char['hp'] + props['heal'])
            healed = new_hp - char['hp']
            await self.db.update_character(char['id'], hp=new_hp)
            effects.append(f"❤️ Restored {healed} HP")
        
        if 'mana' in props:
            new_mana = min(char['max_mana'], char['mana'] + props['mana'])
            restored = new_mana - char['mana']
            await self.db.update_character(char['id'], mana=new_mana)
            effects.append(f"✨ Restored {restored} Mana")
        
        # Remove item
        await self.db.remove_item(item_id, 1)
        
        embed = discord.Embed(
            title=f"🧪 Used {item['item_name']}",
            description="\n".join(effects) or "Item used!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @inventory_group.command(name="equip", description="Equip an item")
    @app_commands.describe(
        item_id="The inventory ID of the item to equip",
        slot="Equipment slot (weapon, armor, helmet, shield, boots, accessory)"
    )
    @app_commands.choices(slot=[
        app_commands.Choice(name=s.title(), value=s) for s in EQUIPMENT_SLOTS
    ])
    async def equip_item(self, interaction: discord.Interaction, item_id: int, slot: str):
        """Equip an item to a slot"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        items = await self.db.get_inventory(char['id'])
        item = next((i for i in items if i['id'] == item_id), None)
        
        if not item:
            await interaction.response.send_message(
                "❌ Item not found!",
                ephemeral=True
            )
            return
        
        if item['item_type'] not in ['weapon', 'armor', 'shield', 'helmet', 'boots', 'accessory']:
            await interaction.response.send_message(
                "❌ This item cannot be equipped!",
                ephemeral=True
            )
            return
        
        result = await self.db.equip_item(item_id, slot)
        
        if 'error' in result:
            await interaction.response.send_message(
                f"❌ {result['error']}",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="⚔️ Item Equipped",
            description=f"Equipped **{item['item_name']}** to {slot} slot!",
            color=discord.Color.green()
        )
        
        # Show stat bonuses if any
        props = item['properties']
        if props:
            bonuses = []
            for key, val in props.items():
                if key.startswith('bonus_'):
                    stat = key.replace('bonus_', '').upper()
                    bonuses.append(f"+{val} {stat}")
            if bonuses:
                embed.add_field(name="Bonuses", value="\n".join(bonuses))
        
        await interaction.response.send_message(embed=embed)
    
    @inventory_group.command(name="unequip", description="Unequip an item")
    @app_commands.describe(item_id="The inventory ID of the item to unequip")
    async def unequip_item(self, interaction: discord.Interaction, item_id: int):
        """Unequip an item"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        await self.db.unequip_item(item_id)
        
        await interaction.response.send_message("✅ Item unequipped!")
    
    @inventory_group.command(name="drop", description="Drop an item from your inventory")
    @app_commands.describe(
        item_id="The inventory ID of the item to drop",
        quantity="Number of items to drop"
    )
    async def drop_item(
        self,
        interaction: discord.Interaction,
        item_id: int,
        quantity: int = 1
    ):
        """Drop an item"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        items = await self.db.get_inventory(char['id'])
        item = next((i for i in items if i['id'] == item_id), None)
        
        if not item:
            await interaction.response.send_message(
                "❌ Item not found!",
                ephemeral=True
            )
            return
        
        await self.db.remove_item(item_id, quantity)
        
        await interaction.response.send_message(
            f"🗑️ Dropped {quantity}x **{item['item_name']}**"
        )
    
    @inventory_group.command(name="give", description="Give an item to another player")
    @app_commands.describe(
        item_id="The inventory ID of the item to give",
        player="The player to give the item to",
        quantity="Number of items to give"
    )
    async def give_item(
        self,
        interaction: discord.Interaction,
        item_id: int,
        player: discord.Member,
        quantity: int = 1
    ):
        """Give an item to another player"""
        giver_char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        receiver_char = await self.db.get_active_character(player.id, interaction.guild.id)
        
        if not giver_char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        if not receiver_char:
            await interaction.response.send_message(
                f"❌ {player.display_name} doesn't have a character!",
                ephemeral=True
            )
            return
        
        items = await self.db.get_inventory(giver_char['id'])
        item = next((i for i in items if i['id'] == item_id), None)
        
        if not item:
            await interaction.response.send_message(
                "❌ Item not found!",
                ephemeral=True
            )
            return
        
        if item['quantity'] < quantity:
            await interaction.response.send_message(
                f"❌ You only have {item['quantity']} of this item!",
                ephemeral=True
            )
            return
        
        # Remove from giver
        await self.db.remove_item(item_id, quantity)
        
        # Add to receiver
        await self.db.add_item(
            receiver_char['id'], item['item_id'], item['item_name'],
            item['item_type'], quantity, item['properties']
        )
        
        await interaction.response.send_message(
            f"🎁 **{giver_char['name']}** gave {quantity}x **{item['item_name']}** to **{receiver_char['name']}**!"
        )
    
    @inventory_group.command(name="shop", description="Visit the shop")
    async def shop(self, interaction: discord.Interaction):
        """Open the shop interface"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message(
                "❌ You don't have a character!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🛒 General Store",
            description=f"Welcome, {char['name']}!\nYour gold: **{char['gold']}** 💰\n\nSelect an item to purchase:",
            color=discord.Color.gold()
        )
        
        for item in SHOP_ITEMS[:5]:
            embed.add_field(
                name=f"{item['name']} - {item['price']} gold",
                value=item['description'],
                inline=False
            )
        
        view = ShopView(self.bot, char['id'])
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Inventory(bot))
