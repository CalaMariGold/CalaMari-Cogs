"""Blackmarket items and views for the crime system."""

import discord
from redbot.core import bank, commands
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time

# Blackmarket Items Configuration
BLACKMARKET_ITEMS = {
    "notify_ping": {
        "name": "Jail Release Notification",
        "emoji": "🔔",
        "cost": 10000,
        "description": "Get notified when you're released from jail. Select in inventory to toggle on/off",
        "type": "perk",
        "effect": "notify_on_release"
    },
    "jail_reducer": {
        "name": "Reduced Sentence",
        "emoji": "⚖️",
        "cost": 20000,
        "description": "Permanently reduce jail time by 20%",
        "type": "perk",
        "effect": "reduce_jail_time",
        "magnitude": 0.2
    }
}

class BlackmarketView(discord.ui.View):
    """View for the blackmarket shop."""
    
    def __init__(self, cog: commands.Cog, ctx: commands.Context):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.message: Optional[discord.Message] = None
        
        # Add select menu for items
        self.add_item(BlackmarketSelect(cog, ctx))

class BlackmarketSelect(discord.ui.Select):
    """Dropdown select menu for blackmarket items."""
    
    def __init__(self, cog: commands.Cog, ctx: commands.Context):
        self.cog = cog
        self.ctx = ctx
        
        # Create options from items
        options = []
        for item_id, item in BLACKMARKET_ITEMS.items():
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    value=item_id,
                    description=f"{item['cost']:,} credits - {item['description']}",
                    emoji=item["emoji"]
                )
            )
            
        super().__init__(
            placeholder="Select an item to purchase...",
            min_values=1,
            max_values=1,
            options=options
        )
        
    async def callback(self, interaction: discord.Interaction):
        """Handle item selection."""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        item_id = self.values[0]
        item = BLACKMARKET_ITEMS[item_id]
        currency_name = await bank.get_currency_name(self.ctx.guild)
        
        # Update option descriptions with currency name
        new_options = []
        for option in self.options:
            item = BLACKMARKET_ITEMS[option.value]
            option.description = f"{item['cost']:,} {currency_name} - {item['description']}"
            new_options.append(option)
        self.options = new_options
        
        try:
            # Check if user can afford
            balance = await bank.get_balance(self.ctx.author)
            if balance < item["cost"]:
                await interaction.response.send_message(
                    f"❌ You cannot afford the {item['name']}! (Cost: {item['cost']:,} {currency_name})",
                    ephemeral=True
                )
                return
                
            # Handle purchase based on item type
            async with self.cog.config.member(self.ctx.author).all() as member_data:
                if item["type"] == "perk":
                    if item_id in member_data.get("purchased_perks", []):
                        await interaction.response.send_message(
                            f"❌ You already own the {item['name']} perk!",
                            ephemeral=True
                        )
                        return
                        
                    # Add perk to user's perks
                    if "purchased_perks" not in member_data:
                        member_data["purchased_perks"] = []
                    member_data["purchased_perks"].append(item_id)
                    
                    # Special handling for notify_ping
                    if item_id == "notify_ping":
                        member_data["notify_unlocked"] = True  # Unlock the feature
                        member_data["notify_on_release"] = True  # Enable notifications by default
                        
                else:  # Consumable
                    if "active_items" not in member_data:
                        member_data["active_items"] = {}
                        
                    # Add item to inventory
                    current_time = int(time.time())
                    if item_id in member_data["active_items"]:
                        # Stack duration for time-based items
                        if "duration" in item:
                            existing_end = member_data["active_items"][item_id].get("end_time", current_time)
                            new_end = max(existing_end, current_time) + item["duration"]
                            member_data["active_items"][item_id] = {
                                "end_time": new_end
                            }
                        else:
                            # Stack uses for use-based items
                            uses = member_data["active_items"][item_id].get("uses", 0) + item["uses"]
                            member_data["active_items"][item_id] = {
                                "uses": uses
                            }
                    else:
                        if "duration" in item:
                            member_data["active_items"][item_id] = {
                                "end_time": current_time + item["duration"]
                            }
                        else:
                            member_data["active_items"][item_id] = {
                                "uses": item["uses"]
                            }
                            
            # Deduct cost
            await bank.withdraw_credits(self.ctx.author, item["cost"])
            
            # Send success message
            if item_id == "notify_ping":
                await interaction.response.send_message(
                    f"✅ Successfully purchased {item['emoji']} **{item['name']}** for {item['cost']:,} {currency_name}!\n"
                    f"Notifications are now enabled by default. Select the perk in your inventory to toggle them on/off.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Successfully purchased {item['emoji']} **{item['name']}** for {item['cost']:,} {currency_name}!",
                    ephemeral=True
                )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred while processing your purchase: {str(e)}",
                ephemeral=True
            )

class InventoryView(discord.ui.View):
    """View for the inventory."""
    
    def __init__(self, cog: commands.Cog, ctx: commands.Context):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.message: Optional[discord.Message] = None
        
        # Create both select menus
        self.activate_select = InventorySelect(cog, ctx)
        self.sell_select = InventorySellSelect(cog, ctx)
        
        # Add them to the view
        self.add_item(self.activate_select)
        self.add_item(self.sell_select)
    
    async def initialize_dropdowns(self) -> None:
        """Initialize both dropdowns when the view is first shown."""
        member_data = await self.cog.config.member(self.ctx.author).all()
        
        # Update both dropdowns
        await self.activate_select.update_options()
        await self.sell_select.update_options()
        
        # Update the message with the new view state
        if self.message:
            await self.message.edit(view=self)

class InventorySelect(discord.ui.Select):
    """Dropdown select menu for activating inventory items."""
    
    def __init__(self, cog: commands.Cog, ctx: commands.Context):
        self.cog = cog
        self.ctx = ctx
        
        # Initialize with a default "empty" option
        options = [
            discord.SelectOption(
                label="No items available",
                value="none",
                description="Purchase items from the black market",
                emoji="❌"
            )
        ]
        
        super().__init__(
            placeholder="Select an item to activate...",
            min_values=1,
            max_values=1,
            options=options,
            disabled=True  # Start disabled until we update options
        )
        
    async def update_options(self) -> None:
        """Update the select menu options based on user's inventory.
        
        Refreshes the dropdown with current items, their uses/duration, and proper formatting.
        Disables the dropdown if no items are available. Handles both consumable items
        and permanent perks, showing appropriate status information for each:
        - Consumables: Shows remaining uses or duration
        - Perks: Shows permanent status and description
        - Time-based items: Shows remaining time in hours/minutes
        """
        member_data = await self.cog.config.member(self.ctx.author).all()
        current_time = int(time.time())
        
        options = []
        
        # Add active consumables
        active_items = member_data.get("active_items", {})
        for item_id, status in active_items.items():
            item = BLACKMARKET_ITEMS[item_id]
            
            if "duration" in item:
                end_time = status.get("end_time", 0)
                if end_time > current_time:
                    remaining = end_time - current_time
                    hours = remaining // 3600
                    minutes = (remaining % 3600) // 60
                    time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                    
                    options.append(
                        discord.SelectOption(
                            label=f"{item['name']} (Active)",
                            value=f"active_{item_id}",
                            description=f"Time remaining: {time_str}",
                            emoji=item["emoji"]
                        )
                    )
            else:
                uses = status.get("uses", 0)
                if uses > 0:
                    options.append(
                        discord.SelectOption(
                            label=f"{item['name']} ({uses} uses)",
                            value=item_id,
                            description=item["description"],
                            emoji=item["emoji"]
                        )
                    )
                    
        # Add owned perks that can be activated (excluding jail_reducer)
        for perk_id in member_data.get("purchased_perks", []):
            # Skip jail reducer perk since it's passive
            if perk_id == "jail_reducer":
                continue
                
            perk = BLACKMARKET_ITEMS[perk_id]
            options.append(
                discord.SelectOption(
                    label=f"{perk['name']} (Permanent)",
                    value=f"perk_{perk_id}",
                    description=perk["description"],
                    emoji=perk["emoji"]
                )
            )
            
        if options:
            self.options = options
            self.disabled = False
        else:
            # If no items, show default "empty" option
            self.options = [
                discord.SelectOption(
                    label="No items available",
                    value="none",
                    description="Purchase items from the black market",
                    emoji="❌"
                )
            ]
            self.disabled = True
        
    async def callback(self, interaction: discord.Interaction):
        """Handle item activation."""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        item_id = self.values[0]
        
        # Handle different item types
        if item_id.startswith("active_"):
            await interaction.response.send_message(
                "This item is already active!",
                ephemeral=True
            )
            return
            
        # Handle notification toggle
        if item_id == "perk_notify_ping":
            try:
                async with self.cog.config.member(self.ctx.author).all() as member_data:
                    member_data["notify_on_release"] = not member_data.get("notify_on_release", False)
                    is_enabled = member_data["notify_on_release"]
                
                embed = discord.Embed(
                    title="🔔 Jail Release Notifications",
                    description=f"Notifications have been {'enabled' if is_enabled else 'disabled'}.\n\n"
                              f"You will{' ' if is_enabled else ' not '}be pinged when your jail sentence is over.",
                    color=discord.Color.green() if is_enabled else discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ An error occurred while toggling notifications: {str(e)}",
                    ephemeral=True
                )
                return
            
        # Handle consumable activation
        try:
            item = BLACKMARKET_ITEMS[item_id]
            
            async with self.cog.config.member(self.ctx.author).all() as member_data:
                if item_id not in member_data.get("active_items", {}):
                    await interaction.response.send_message(
                        "❌ You don't have this item!",
                        ephemeral=True
                    )
                    return
                    
                # Special handling for different items
                if item_id == "jail_card":
                    # Check if in jail
                    if not await self.cog.is_jailed(self.ctx.author):
                        await interaction.response.send_message(
                            "❌ You're not in jail!",
                            ephemeral=True
                        )
                        return
                        
                    # Free from jail
                    await self.cog.config.member(self.ctx.author).jail_until.set(0)
                    
                    # Remove one use
                    member_data["active_items"][item_id]["uses"] -= 1
                    if member_data["active_items"][item_id]["uses"] <= 0:
                        del member_data["active_items"][item_id]
                        
                    await interaction.response.send_message(
                        "🔓 You used your Get Out of Jail Free card and were released!",
                        ephemeral=False
                    )
                    
            # Update options after use
            await self.update_options()
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred while activating your item: {str(e)}",
                ephemeral=True
            )

class InventorySellSelect(discord.ui.Select):
    """Dropdown select menu for selling inventory items."""
    
    def __init__(self, cog: commands.Cog, ctx: commands.Context):
        self.cog = cog
        self.ctx = ctx
        
        # Initialize with a default "empty" option
        options = [
            discord.SelectOption(
                label="No items available",
                value="none",
                description="Purchase items from the black market",
                emoji="❌"
            )
        ]
        
        super().__init__(
            placeholder="Select an item to sell...",
            min_values=1,
            max_values=1,
            options=options,
            disabled=True  # Start disabled until we update options
        )
        
    async def update_options(self) -> None:
        """Update the select menu options based on user's inventory."""
        member_data = await self.cog.config.member(self.ctx.author).all()
        currency_name = await bank.get_currency_name(self.ctx.guild)
        options = []
        
        # Add owned perks first
        perks = member_data.get("purchased_perks", [])
        for perk_id in perks:
            if perk_id in BLACKMARKET_ITEMS:  # Make sure the perk exists
                perk = BLACKMARKET_ITEMS[perk_id]
                sell_price = int(perk["cost"] * 0.25)  # 25% refund for perks
                options.append(
                    discord.SelectOption(
                        label=f"{perk['name']} (Permanent)",
                        value=f"perk_{perk_id}",
                        description=f"Sell for {sell_price:,} {currency_name}",
                        emoji=perk["emoji"]
                    )
                )
        
        # Add sellable items (consumables)
        active_items = member_data.get("active_items", {})
        for item_id, status in active_items.items():
            if item_id in BLACKMARKET_ITEMS:  # Make sure the item exists
                item = BLACKMARKET_ITEMS[item_id]
                uses = status.get("uses", 0)
                if uses > 0:
                    sell_price = int(item["cost"] * 0.5)  # 50% refund
                    options.append(
                        discord.SelectOption(
                            label=f"{item['name']} ({uses} uses)",
                            value=item_id,
                            description=f"Sell for {sell_price:,} {currency_name}",
                            emoji=item["emoji"]
                        )
                    )
            
        if options:
            self.options = options
            self.disabled = False
        else:
            # If no items, show default "empty" option
            self.options = [
                discord.SelectOption(
                    label="No items available",
                    value="none",
                    description="Purchase items from the black market",
                    emoji="❌"
                )
            ]
            self.disabled = True
        
    async def callback(self, interaction: discord.Interaction):
        """Handle item selling."""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        item_id = self.values[0]
        currency_name = await bank.get_currency_name(self.ctx.guild)
        
        # Handle different item types
        try:
            async with self.cog.config.member(self.ctx.author).all() as member_data:
                if item_id.startswith("perk_"):
                    # Handle perk selling
                    perk_id = item_id[5:]  # Remove "perk_" prefix
                    if perk_id not in member_data.get("purchased_perks", []):
                        await interaction.response.send_message(
                            "❌ You don't own this perk!",
                            ephemeral=True
                        )
                        return
                        
                    perk = BLACKMARKET_ITEMS[perk_id]
                    sell_price = int(perk["cost"] * 0.25)  # 25% refund
                    
                    # Remove perk
                    member_data["purchased_perks"].remove(perk_id)
                    
                    # If it's the notification perk, disable notifications
                    if perk_id == "notify_ping":
                        member_data["notify_on_release"] = False
                        member_data["notify_unlocked"] = False
                    
                    # Give credits
                    await bank.deposit_credits(self.ctx.author, sell_price)
                    
                    embed = discord.Embed(
                        title="💰 Item Sold",
                        description=f"You sold your {perk['emoji']} {perk['name']} for {sell_price:,} {currency_name}.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed)
                    
                else:
                    # Handle consumable selling
                    if item_id not in member_data.get("active_items", {}):
                        await interaction.response.send_message(
                            "❌ You don't have this item!",
                            ephemeral=True
                        )
                        return
                        
                    item = BLACKMARKET_ITEMS[item_id]
                    uses = member_data["active_items"][item_id].get("uses", 0)
                    sell_price = int(item["cost"] * 0.5 * uses)  # 50% refund per use
                    
                    # Remove item
                    del member_data["active_items"][item_id]
                    
                    # Give credits
                    await bank.deposit_credits(self.ctx.author, sell_price)
                    
                    embed = discord.Embed(
                        title="💰 Item Sold",
                        description=f"You sold your {item['emoji']} {item['name']} ({uses} uses) for {sell_price:,} {currency_name}.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed)
                    
            # Update both dropdowns after selling
            await self.update_options()
            for child in self.view.children:
                if isinstance(child, InventorySelect):
                    await child.update_options()
                    
            # Update the message with new dropdowns
            await self.view.message.edit(view=self.view)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred while selling the item: {str(e)}",
                ephemeral=True
            ) 