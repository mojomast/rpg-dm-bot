"""
RPG DM Bot - Inventory Cog
Handles item management, equipment, and shops with interactive buttons
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
import os
import random
from typing import List, Dict, Any, Optional

logger = logging.getLogger('rpg.inventory')

# Load items data
ITEMS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'game_data', 'items.json')
ITEMS_DATA = {}

def load_items():
    global ITEMS_DATA
    try:
        with open(ITEMS_FILE, 'r', encoding='utf-8') as f:
            ITEMS_DATA = json.load(f)
    except FileNotFoundError:
        ITEMS_DATA = {}

load_items()

# Equipment slots mapping
EQUIPMENT_SLOTS = {
    "main_hand": "Main Hand",
    "off_hand": "Off Hand", 
    "two_hand": "Two Hands",
    "head": "Head",
    "body": "Body",
    "back": "Back",
    "hands": "Hands",
    "waist": "Waist",
    "feet": "Feet",
    "neck": "Neck",
    "ring": "Ring",
    "arms": "Arms"
}

# Rarity colors
RARITY_COLORS = {
    "common": discord.Color.light_grey(),
    "uncommon": discord.Color.green(),
    "rare": discord.Color.blue(),
    "very_rare": discord.Color.purple(),
    "legendary": discord.Color.orange(),
    "quest": discord.Color.gold()
}

def get_item_data(item_id: str) -> Optional[Dict]:
    """Get item data from items.json by ID"""
    for category in ['weapons', 'armor', 'consumables', 'accessories', 'gear', 'ammunition', 'quest_items', 'materials']:
        items = ITEMS_DATA.get(category, [])
        for item in items:
            if item.get('id') == item_id:
                return item
    return None

def get_shop_items() -> List[Dict]:
    """Get all purchasable items for shop"""
    shop_items = []
    for category in ['weapons', 'armor', 'consumables', 'accessories', 'gear', 'ammunition']:
        for item in ITEMS_DATA.get(category, []):
            if item.get('price', 0) > 0:
                shop_items.append(item)
    return sorted(shop_items, key=lambda x: x.get('price', 0))


class ShopView(discord.ui.View):
    """View for browsing and purchasing shop items"""
    
    def __init__(self, bot, character_id: int, category: str = "all"):
        super().__init__(timeout=300)
        self.bot = bot
        self.character_id = character_id
        self.category = category
        self.page = 0
        self.items_per_page = 5
        
        # Add category dropdown
        self.add_item(ShopCategoryDropdown(bot, character_id))
    
    def get_filtered_items(self) -> List[Dict]:
        """Get items filtered by category"""
        shop_items = get_shop_items()
        if self.category == "all":
            return shop_items
        return [i for i in shop_items if i.get('type') == self.category or i.get('subtype') == self.category]
    
    def get_page_items(self) -> List[Dict]:
        items = self.get_filtered_items()
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        return items[start:end]
    
    async def update_embed(self, interaction: discord.Interaction):
        char = await self.bot.db.get_character(self.character_id)
        items = self.get_page_items()
        total_items = len(self.get_filtered_items())
        
        embed = discord.Embed(
            title="🛒 General Store",
            description=f"Your gold: **{char['gold']}** 💰\n\nCategory: **{self.category.title()}**",
            color=discord.Color.gold()
        )
        
        for item in items:
            rarity = item.get('rarity', 'common')
            rarity_icon = {"common": "⬜", "uncommon": "🟢", "rare": "🔵", "very_rare": "🟣", "legendary": "🟠"}.get(rarity, "⬜")
            
            name = f"{rarity_icon} {item['name']} - {item.get('price', 0)} gold"
            desc = item.get('description', 'No description')[:100]
            
            # Add key stats
            stats = []
            if item.get('damage'):
                stats.append(f"⚔️ {item['damage']}")
            if item.get('ac_base'):
                stats.append(f"🛡️ AC {item['ac_base']}")
            if item.get('ac_bonus'):
                stats.append(f"🛡️ +{item['ac_bonus']} AC")
            
            if stats:
                desc += f"\n{' | '.join(stats)}"
            
            embed.add_field(name=name, value=desc, inline=False)
        
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} | {total_items} items")
        
        # Update buy dropdown
        for child in self.children:
            if isinstance(child, ShopBuyDropdown):
                self.remove_item(child)
        
        if items:
            self.add_item(ShopBuyDropdown(self.bot, self.character_id, items))
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, row=2)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self.update_embed(interaction)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, row=2)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_items = len(self.get_filtered_items())
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        if self.page < total_pages - 1:
            self.page += 1
        await self.update_embed(interaction)


class ShopCategoryDropdown(discord.ui.Select):
    """Dropdown to filter shop by category"""
    
    def __init__(self, bot, character_id: int):
        self.bot = bot
        self.character_id = character_id
        
        options = [
            discord.SelectOption(label="All Items", value="all", emoji="📦"),
            discord.SelectOption(label="Weapons", value="weapon", emoji="⚔️"),
            discord.SelectOption(label="Armor", value="armor", emoji="🛡️"),
            discord.SelectOption(label="Consumables", value="consumable", emoji="🧪"),
            discord.SelectOption(label="Accessories", value="accessory", emoji="💍"),
            discord.SelectOption(label="Gear", value="gear", emoji="🎒"),
            discord.SelectOption(label="Ammunition", value="ammunition", emoji="🏹"),
        ]
        
        super().__init__(placeholder="📂 Filter by category...", options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        self.view.category = self.values[0]
        self.view.page = 0
        await self.view.update_embed(interaction)


class ShopBuyDropdown(discord.ui.Select):
    """Dropdown to select item to buy"""
    
    def __init__(self, bot, character_id: int, items: List[Dict]):
        self.bot = bot
        self.character_id = character_id
        self.item_map = {i['id']: i for i in items}
        
        options = []
        for item in items[:25]:
            options.append(discord.SelectOption(
                label=f"{item['name']} ({item.get('price', 0)}g)",
                value=item['id'],
                description=item.get('description', '')[:50]
            ))
        
        super().__init__(
            placeholder="🛒 Select item to buy...", 
            options=options if options else [discord.SelectOption(label="No items", value="none")],
            row=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return
        
        item_id = self.values[0]
        item = self.item_map.get(item_id)
        
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return
        
        char = await self.bot.db.get_character(self.character_id)
        price = item.get('price', 0)
        
        if char['gold'] < price:
            await interaction.response.send_message(
                f"❌ Not enough gold! You have {char['gold']}, need {price}.",
                ephemeral=True
            )
            return
        
        # Purchase item
        await self.bot.db.update_gold(self.character_id, -price)
        
        # Build properties dict from item data
        props = {}
        for key in ['damage', 'damage_type', 'ac_base', 'ac_bonus', 'bonus_attack', 'bonus_damage', 
                    'properties', 'effect', 'spell_power_bonus', 'stat_bonus', 'stat_set']:
            if key in item:
                props[key] = item[key]
        
        await self.bot.db.add_item(
            self.character_id, item['id'], item['name'],
            item.get('type', 'misc'), 1, props
        )
        
        await interaction.response.send_message(
            f"✅ Purchased **{item['name']}** for {price} gold!",
            ephemeral=True
        )


# ============================================================================
# INVENTORY VIEW
# ============================================================================

class InventoryView(discord.ui.View):
    """Interactive inventory view with item management"""
    
    def __init__(self, bot, character: Dict, items: List[Dict]):
        super().__init__(timeout=180)
        self.bot = bot
        self.character = character
        self.items = items
        self.filter_type = "all"
        
        if items:
            self.add_item(InventoryFilterDropdown())
            self.add_item(InventoryActionDropdown(bot, character, items))
    
    def get_filtered_items(self) -> List[Dict]:
        if self.filter_type == "all":
            return self.items
        return [i for i in self.items if i['item_type'] == self.filter_type]
    
    @discord.ui.button(label="🎒 Equipment", style=discord.ButtonStyle.primary, row=2)
    async def view_equipment(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show equipped items"""
        equipped = [i for i in self.items if i.get('is_equipped')]
        
        embed = discord.Embed(
            title=f"⚔️ {self.character['name']}'s Equipment",
            color=discord.Color.gold()
        )
        
        # Group by slot
        by_slot = {}
        for item in equipped:
            slot = item.get('slot', 'Unknown')
            by_slot[slot] = item
        
        for slot_id, slot_name in EQUIPMENT_SLOTS.items():
            item = by_slot.get(slot_id)
            if item:
                item_data = get_item_data(item['item_id'])
                rarity = item_data.get('rarity', 'common') if item_data else 'common'
                rarity_icon = {"common": "⬜", "uncommon": "🟢", "rare": "🔵", "very_rare": "🟣", "legendary": "🟠"}.get(rarity, "⬜")
                embed.add_field(name=slot_name, value=f"{rarity_icon} {item['item_name']}", inline=True)
            else:
                embed.add_field(name=slot_name, value="*Empty*", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🧪 Use Item", style=discord.ButtonStyle.success, row=2)
    async def use_item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show consumables to use"""
        consumables = [i for i in self.items if i['item_type'] == 'consumable']
        
        if not consumables:
            await interaction.response.send_message("❌ No consumable items!", ephemeral=True)
            return
        
        view = UseItemView(self.bot, self.character, consumables)
        await interaction.response.send_message(
            "🧪 Select an item to use:",
            view=view,
            ephemeral=True
        )


class InventoryFilterDropdown(discord.ui.Select):
    """Filter inventory by item type"""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="All Items", value="all", emoji="📦"),
            discord.SelectOption(label="Weapons", value="weapon", emoji="⚔️"),
            discord.SelectOption(label="Armor", value="armor", emoji="🛡️"),
            discord.SelectOption(label="Consumables", value="consumable", emoji="🧪"),
            discord.SelectOption(label="Accessories", value="accessory", emoji="💍"),
            discord.SelectOption(label="Gear", value="gear", emoji="🎒"),
        ]
        super().__init__(placeholder="📂 Filter items...", options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        self.view.filter_type = self.values[0]
        
        items = self.view.get_filtered_items()
        
        embed = discord.Embed(
            title=f"🎒 {self.view.character['name']}'s Inventory",
            description=f"💰 Gold: **{self.view.character['gold']}** | Filter: **{self.values[0].title()}**",
            color=discord.Color.blue()
        )
        
        if not items:
            embed.add_field(name="Items", value="No items in this category!", inline=False)
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
                for item in type_items[:10]:
                    item_data = get_item_data(item['item_id'])
                    rarity = item_data.get('rarity', 'common') if item_data else 'common'
                    rarity_icon = {"common": "⬜", "uncommon": "🟢", "rare": "🔵", "very_rare": "🟣", "legendary": "🟠"}.get(rarity, "⬜")
                    
                    equipped = "⚔️ " if item.get('is_equipped') else ""
                    qty = f" x{item['quantity']}" if item['quantity'] > 1 else ""
                    lines.append(f"{equipped}{rarity_icon} [{item['id']}] {item['item_name']}{qty}")
                
                if len(type_items) > 10:
                    lines.append(f"*...and {len(type_items) - 10} more*")
                
                embed.add_field(
                    name=f"{item_type.title()}s ({len(type_items)})",
                    value="\n".join(lines) or "None",
                    inline=False
                )
        
        await interaction.response.edit_message(embed=embed)


class InventoryActionDropdown(discord.ui.Select):
    """Select an item to perform actions on"""
    
    def __init__(self, bot, character: Dict, items: List[Dict]):
        self.bot = bot
        self.character = character
        self.item_map = {i['id']: i for i in items}
        
        options = []
        for item in items[:25]:
            equipped = "⚔️ " if item.get('is_equipped') else ""
            options.append(discord.SelectOption(
                label=f"{equipped}{item['item_name']}"[:50],
                value=str(item['id']),
                description=f"ID: {item['id']} | Type: {item['item_type']}"
            ))
        
        super().__init__(
            placeholder="🔍 Select item for details...",
            options=options if options else [discord.SelectOption(label="No items", value="0")],
            row=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "0":
            return
        
        item_id = int(self.values[0])
        item = self.item_map.get(item_id)
        
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return
        
        item_data = get_item_data(item['item_id'])
        rarity = item_data.get('rarity', 'common') if item_data else 'common'
        color = RARITY_COLORS.get(rarity, discord.Color.light_grey())
        
        embed = discord.Embed(
            title=f"📦 {item['item_name']}",
            description=item_data.get('description', 'No description') if item_data else 'No data',
            color=color
        )
        
        embed.add_field(name="Type", value=item['item_type'].title(), inline=True)
        embed.add_field(name="Rarity", value=rarity.replace('_', ' ').title(), inline=True)
        embed.add_field(name="Quantity", value=str(item['quantity']), inline=True)
        
        if item.get('is_equipped'):
            embed.add_field(name="Status", value="⚔️ Equipped", inline=True)
        
        # Show stats
        if item_data:
            if item_data.get('damage'):
                dmg_type = item_data.get('damage_type', 'physical')
                embed.add_field(name="Damage", value=f"{item_data['damage']} {dmg_type}", inline=True)
            if item_data.get('ac_base'):
                embed.add_field(name="AC", value=str(item_data['ac_base']), inline=True)
            if item_data.get('ac_bonus'):
                embed.add_field(name="AC Bonus", value=f"+{item_data['ac_bonus']}", inline=True)
            if item_data.get('weight'):
                embed.add_field(name="Weight", value=str(item_data['weight']), inline=True)
            if item_data.get('price'):
                embed.add_field(name="Value", value=f"{item_data['price']} gold", inline=True)
        
        view = ItemActionView(self.bot, self.character, item)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ItemActionView(discord.ui.View):
    """Actions for a specific item"""
    
    def __init__(self, bot, character: Dict, item: Dict):
        super().__init__(timeout=60)
        self.bot = bot
        self.character = character
        self.item = item
        
        # Add appropriate buttons based on item type
        item_data = get_item_data(item['item_id'])
        
        if item['item_type'] == 'consumable':
            self.add_item(UseItemButton(bot, character, item))
        elif item['item_type'] in ['weapon', 'armor', 'accessory']:
            if item.get('is_equipped'):
                self.add_item(UnequipItemButton(bot, character, item))
            else:
                slot = item_data.get('slot', 'main_hand') if item_data else 'main_hand'
                self.add_item(EquipItemButton(bot, character, item, slot))
    
    @discord.ui.button(label="🗑️ Drop", style=discord.ButtonStyle.danger, row=1)
    async def drop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.remove_item(self.item['id'], 1)
        await interaction.response.send_message(
            f"🗑️ Dropped **{self.item['item_name']}**",
            ephemeral=True
        )
        self.stop()


class UseItemButton(discord.ui.Button):
    """Button to use a consumable item"""
    
    def __init__(self, bot, character: Dict, item: Dict):
        super().__init__(label="🧪 Use", style=discord.ButtonStyle.success)
        self.bot = bot
        self.character = character
        self.item = item
    
    async def callback(self, interaction: discord.Interaction):
        item_data = get_item_data(self.item['item_id'])
        
        if not item_data:
            await interaction.response.send_message("❌ Item data not found!", ephemeral=True)
            return
        
        # Process effects
        effects = []
        effect = item_data.get('effect', {})
        
        char = await self.bot.db.get_character(self.character['id'])
        
        if effect.get('type') == 'heal':
            value = effect.get('value', '0')
            healed = roll_dice(value) if isinstance(value, str) else value
            new_hp = min(char['max_hp'], char['hp'] + healed)
            actual_healed = new_hp - char['hp']
            await self.bot.db.update_character(self.character['id'], hp=new_hp)
            effects.append(f"❤️ Restored **{actual_healed}** HP")
        
        elif effect.get('type') == 'restore_mana':
            value = effect.get('value', 0)
            new_mana = min(char['max_mana'], char['mana'] + value)
            actual_restored = new_mana - char['mana']
            await self.bot.db.update_character(self.character['id'], mana=new_mana)
            effects.append(f"✨ Restored **{actual_restored}** Mana")
        
        elif effect.get('type') == 'buff':
            stat = effect.get('stat', 'strength')
            value = effect.get('value', 1)
            duration = effect.get('duration', 60)
            effects.append(f"⬆️ +{value} {stat} for {duration} seconds")
            # Could apply status effect here
        
        elif effect.get('type') == 'cure':
            status = effect.get('status', 'poisoned')
            effects.append(f"💊 Cured **{status}** condition")
        
        # Remove item
        await self.bot.db.remove_item(self.item['id'], 1)
        
        embed = discord.Embed(
            title=f"🧪 Used {self.item['item_name']}",
            description="\n".join(effects) or "Item used!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.view.stop()


class EquipItemButton(discord.ui.Button):
    """Button to equip an item"""
    
    def __init__(self, bot, character: Dict, item: Dict, slot: str):
        super().__init__(label=f"⚔️ Equip ({EQUIPMENT_SLOTS.get(slot, slot)})", style=discord.ButtonStyle.primary)
        self.bot = bot
        self.character = character
        self.item = item
        self.slot = slot
    
    async def callback(self, interaction: discord.Interaction):
        result = await self.bot.db.equip_item(self.item['id'], self.slot)
        
        if isinstance(result, dict) and 'error' in result:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚔️ Item Equipped",
            description=f"Equipped **{self.item['item_name']}** to {EQUIPMENT_SLOTS.get(self.slot, self.slot)}!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.view.stop()


class UnequipItemButton(discord.ui.Button):
    """Button to unequip an item"""
    
    def __init__(self, bot, character: Dict, item: Dict):
        super().__init__(label="📤 Unequip", style=discord.ButtonStyle.secondary)
        self.bot = bot
        self.character = character
        self.item = item
    
    async def callback(self, interaction: discord.Interaction):
        await self.bot.db.unequip_item(self.item['id'])
        
        await interaction.response.send_message(
            f"📤 Unequipped **{self.item['item_name']}**",
            ephemeral=True
        )
        self.view.stop()


class UseItemView(discord.ui.View):
    """View for selecting and using consumable items"""
    
    def __init__(self, bot, character: Dict, consumables: List[Dict]):
        super().__init__(timeout=60)
        self.bot = bot
        self.character = character
        
        if consumables:
            self.add_item(UseItemDropdown(bot, character, consumables))


class UseItemDropdown(discord.ui.Select):
    """Dropdown to select consumable to use"""
    
    def __init__(self, bot, character: Dict, consumables: List[Dict]):
        self.bot = bot
        self.character = character
        self.item_map = {i['id']: i for i in consumables}
        
        options = []
        for item in consumables[:25]:
            item_data = get_item_data(item['item_id'])
            desc = item_data.get('description', '')[:50] if item_data else ''
            qty = f" x{item['quantity']}" if item['quantity'] > 1 else ""
            
            options.append(discord.SelectOption(
                label=f"{item['item_name']}{qty}",
                value=str(item['id']),
                description=desc
            ))
        
        super().__init__(placeholder="🧪 Select item to use...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        item = self.item_map.get(item_id)
        
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return
        
        # Create a button to trigger the use
        button = UseItemButton(self.bot, self.character, item)
        # Manually call the callback
        await button.callback(interaction)


def roll_dice(dice_string: str) -> int:
    """Roll dice and return total (e.g., '2d4+2')"""
    try:
        total = 0
        parts = dice_string.replace('-', '+-').split('+')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if 'd' in part.lower():
                num, sides = part.lower().split('d')
                num = int(num) if num else 1
                sides = int(sides)
                for _ in range(abs(num)):
                    roll = random.randint(1, sides)
                    total += roll if num > 0 else -roll
            else:
                total += int(part)
        
        return max(0, total)
    except:
        return 0


class Inventory(commands.Cog):
    """Inventory management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        return self.bot.db
    
    inventory_group = app_commands.Group(
        name="inventory", 
        description="Inventory commands",
        guild_only=True
    )
    
    @inventory_group.command(name="view", description="View your inventory")
    async def view_inventory(self, interaction: discord.Interaction):
        """Display inventory contents with interactive view"""
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
                for item in type_items[:10]:
                    item_data = get_item_data(item['item_id'])
                    rarity = item_data.get('rarity', 'common') if item_data else 'common'
                    rarity_icon = {"common": "⬜", "uncommon": "🟢", "rare": "🔵", "very_rare": "🟣", "legendary": "🟠"}.get(rarity, "⬜")
                    
                    equipped = "⚔️ " if item['is_equipped'] else ""
                    qty = f" x{item['quantity']}" if item['quantity'] > 1 else ""
                    lines.append(f"{equipped}{rarity_icon} [{item['id']}] {item['item_name']}{qty}")
                
                if len(type_items) > 10:
                    lines.append(f"*...and {len(type_items) - 10} more*")
                
                embed.add_field(
                    name=f"{item_type.title()}s ({len(type_items)})",
                    value="\n".join(lines) or "None",
                    inline=False
                )
        
        view = InventoryView(self.bot, char, items) if items else None
        await interaction.response.send_message(embed=embed, view=view)
    
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
        
        shop_items = get_shop_items()
        
        embed = discord.Embed(
            title="🛒 General Store",
            description=f"Welcome, {char['name']}!\nYour gold: **{char['gold']}** 💰\n\nBrowse items by category:",
            color=discord.Color.gold()
        )
        
        # Show first 5 items
        for item in shop_items[:5]:
            rarity = item.get('rarity', 'common')
            rarity_icon = {"common": "⬜", "uncommon": "🟢", "rare": "🔵", "very_rare": "🟣", "legendary": "🟠"}.get(rarity, "⬜")
            embed.add_field(
                name=f"{rarity_icon} {item['name']} - {item.get('price', 0)} gold",
                value=item.get('description', 'No description')[:100],
                inline=False
            )
        
        total_pages = max(1, (len(shop_items) + 4) // 5)
        embed.set_footer(text=f"Page 1/{total_pages} | {len(shop_items)} items available")
        
        view = ShopView(self.bot, char['id'])
        await interaction.response.send_message(embed=embed, view=view)
    
    @inventory_group.command(name="quickuse", description="Quickly use an item by name")
    @app_commands.describe(item_name="Name of the item to use")
    async def quick_use(self, interaction: discord.Interaction, item_name: str):
        """Quickly use an item without the full inventory interface"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            await interaction.response.send_message("❌ You don't have a character!", ephemeral=True)
            return
        
        items = await self.db.get_inventory(char['id'])
        
        # Find matching item
        item = None
        for i in items:
            if item_name.lower() in i['item_name'].lower():
                if i['item_type'] == 'consumable':
                    item = i
                    break
        
        if not item:
            await interaction.response.send_message(
                f"❌ No consumable item matching **{item_name}** found!",
                ephemeral=True
            )
            return
        
        item_data = get_item_data(item['item_id'])
        
        if not item_data:
            await interaction.response.send_message("❌ Item data not found!", ephemeral=True)
            return
        
        # Process effects
        effects = []
        effect = item_data.get('effect', {})
        
        if effect.get('type') == 'heal':
            value = effect.get('value', '0')
            healed = roll_dice(value) if isinstance(value, str) else value
            new_hp = min(char['max_hp'], char['hp'] + healed)
            actual_healed = new_hp - char['hp']
            await self.db.update_character(char['id'], hp=new_hp)
            effects.append(f"❤️ Restored **{actual_healed}** HP")
        
        elif effect.get('type') == 'restore_mana':
            value = effect.get('value', 0)
            new_mana = min(char['max_mana'], char['mana'] + value)
            actual_restored = new_mana - char['mana']
            await self.db.update_character(char['id'], mana=new_mana)
            effects.append(f"✨ Restored **{actual_restored}** Mana")
        
        elif effect.get('type') == 'cure':
            status = effect.get('status', 'poisoned')
            effects.append(f"💊 Cured **{status}** condition")
        
        # Remove item
        await self.db.remove_item(item['id'], 1)
        
        embed = discord.Embed(
            title=f"🧪 Used {item['item_name']}",
            description="\n".join(effects) or "Item used!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @quick_use.autocomplete('item_name')
    async def item_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for item names"""
        char = await self.db.get_active_character(interaction.user.id, interaction.guild.id)
        
        if not char:
            return []
        
        items = await self.db.get_inventory(char['id'])
        choices = []
        
        for item in items:
            if item['item_type'] == 'consumable':
                if current.lower() in item['item_name'].lower():
                    choices.append(app_commands.Choice(
                        name=item['item_name'][:100],
                        value=item['item_name'][:100]
                    ))
        
        return choices[:25]


async def setup(bot):
    await bot.add_cog(Inventory(bot))
