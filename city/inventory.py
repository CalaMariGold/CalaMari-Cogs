"""Inventory system for the City cog.

This module provides a flexible inventory system that can be used by any module
in the City cog. It supports both consumable and permanent items, with features
for activating and selling items.

The system is designed to be extensible, allowing different modules to register
their own items with custom activation and sale behaviors.

"""

from typing import Dict, List, Optional, Union, Any, Tuple, Callable
import discord
from redbot.core import bank, commands
import time
from datetime import datetime, timedelta
import asyncio

async def cleanup_inventory(member_data: Dict[str, Any], item_registry: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Clean up expired or invalid items from member data.
    
    Args:
        member_data (Dict[str, Any]): The member's data containing inventory and perks
        item_registry (Dict[str, Dict[str, Any]]): Registry of available items
        
    Returns:
        Dict[str, Any]: The cleaned member data
    """
    current_time = int(time.time())
    
    # Clean up active items
    if "active_items" in member_data:
        active_items = member_data["active_items"]
        to_remove = []
        
        for item_id, status in active_items.items():
            # Remove if item no longer exists in registry
            if item_id not in item_registry:
                to_remove.append(item_id)
                continue
            
            item = item_registry[item_id]
            if "duration" in item:
                # Remove if duration expired
                end_time = status.get("end_time", 0)
                if end_time <= current_time:
                    to_remove.append(item_id)
            elif "uses" in status:
                # Remove if no uses left
                if status["uses"] <= 0:
                    to_remove.append(item_id)
        
        for item_id in to_remove:
            del active_items[item_id]
    
    # Clean up purchased perks
    if "purchased_perks" in member_data:
        # Remove perks that no longer exist in registry
        member_data["purchased_perks"] = [
            perk_id for perk_id in member_data["purchased_perks"]
            if perk_id in item_registry
        ]
    
    return member_data

class InventoryView(discord.ui.View):
    """A view for displaying and managing a user's inventory.
    
    This view provides functionality for activating and selling items from the user's inventory.
    It supports both consumable and permanent items, with appropriate handling for each type.
    
    Attributes:
        ctx (commands.Context): The command context
        cog (commands.Cog): The cog instance that created this view
        member_data (Dict[str, Any]): The member's data containing inventory and perks
        item_registry (Dict[str, Dict[str, Any]]): Registry of available items
        message (Optional[discord.Message]): The message containing this view
    """
    
    def __init__(self, ctx: commands.Context, cog: commands.Cog, member_data: Dict[str, Any], item_registry: Dict[str, Dict[str, Any]]) -> None:
        super().__init__(timeout=180)
        self.ctx = ctx
        self.cog = cog
        self.member_data = member_data
        self.item_registry = item_registry
        self.message: Optional[discord.Message] = None
        
    async def _update_options(self) -> None:
        """Update the select menu options based on the user's inventory."""
        # Clear existing options
        for child in self.children[:]:
            self.remove_item(child)
            
        current_time = int(time.time())
        owned_items = []
        currency_name = await bank.get_currency_name(self.ctx.guild)
        
        # Add owned perks
        for perk_id in self.member_data.get("purchased_perks", []):
            if perk_id in self.item_registry:
                owned_items.append((perk_id, self.item_registry[perk_id], None))
        
        # Add active items
        for item_id, status in self.member_data.get("active_items", {}).items():
            if item_id not in self.item_registry:
                continue
                
            item = self.item_registry[item_id]
            if "duration" in item:
                end_time = status.get("end_time", 0)
                if end_time > current_time:
                    remaining = end_time - current_time
                    owned_items.append((item_id, item, f"{remaining // 3600}h {(remaining % 3600) // 60}m remaining"))
            elif "uses" in status:
                uses = status.get("uses", 0)
                if uses > 0:
                    owned_items.append((item_id, item, f"{uses} uses remaining"))
            
        if not owned_items:
            # Add placeholder if no items
            self.add_item(discord.ui.Select(
                placeholder="No items in inventory",
                options=[discord.SelectOption(label="Empty", value="empty", description="Your inventory is empty")],
                disabled=True
            ))
            return
            
        # Add activation select
        activate_options = []
        for item_id, item, status in owned_items:
            # Skip perks that aren't toggleable
            if item["type"] == "perk" and not item.get("toggleable", False):
                continue
                
            description = item["description"]
            if status:
                description = f"{status} - {description}"
            
            if item_id == "notify_ping":
                current_status = self.member_data.get("notify_on_release", False)
                label = f"{item['name']} ({'Enabled' if current_status else 'Disabled'})"
            else:
                label = item['name']
                
            activate_options.append(
                discord.SelectOption(
                    label=label,
                    value=f"activate_{item_id}",
                    description=description,
                    emoji=item.get("emoji", "📦")
                )
            )
        
        if activate_options:
            activate_select = discord.ui.Select(
                placeholder="Select an item to use/toggle",
                options=activate_options,
                row=0
            )
            activate_select.callback = self._handle_activation
            self.add_item(activate_select)
        
        # Add sell select for sellable items
        sell_options = []
        for item_id, item, status in owned_items:
            if not item.get("can_sell", True):
                continue
                
            sell_price = int(item["cost"] * (0.25 if item["type"] == "perk" else 0.5))
            
            description = f"Sell for {sell_price:,} {currency_name}"
            if status:
                description = f"{status} - {description}"
            
            sell_options.append(
                discord.SelectOption(
                    label=f"Sell {item['name']}",
                    value=f"sell_{item_id}",
                    description=description,
                    emoji="💰"
                )
            )
        
        if sell_options:
            sell_select = discord.ui.Select(
                placeholder="Select an item to sell",
                options=sell_options,
                row=1
            )
            sell_select.callback = self._handle_sale
            self.add_item(sell_select)
    
    async def _create_embed(self) -> discord.Embed:
        """Create the inventory embed.
        
        Returns:
            discord.Embed: The created embed
        """
        embed = discord.Embed(
            title="🎒 Your Inventory",
            description="Select an item to activate or sell it.",
            color=discord.Color.blue()
        )
        
        # Add perks section
        perks = []
        for perk_id in self.member_data.get("purchased_perks", []):
            if perk_id in self.item_registry:
                perk = self.item_registry[perk_id]
                status = ""
                if perk_id == "notify_ping":
                    status = " (Enabled)" if self.member_data.get("notify_on_release", False) else " (Disabled)"
                perks.append(f"{perk['emoji']} **{perk['name']}**{status}\n↳ {perk['description']}")
        
        if perks:
            embed.add_field(
                name="__🔒 Permanent Perks__",
                value="\n".join(perks),
                inline=False
            )
        
        # Add active items section
        current_time = int(time.time())
        active_items = []
        for item_id, status in self.member_data.get("active_items", {}).items():
            if item_id not in self.item_registry:
                continue
                
            item = self.item_registry[item_id]
            if "duration" in item:
                end_time = status.get("end_time", 0)
                if end_time > current_time:
                    remaining = end_time - current_time
                    time_str = format_time_remaining(remaining)
                    active_items.append(f"{item['emoji']} **{item['name']}**\n↳ Time remaining: {time_str}")
            else:
                uses = status.get("uses", 0)
                if uses > 0:
                    active_items.append(f"{item['emoji']} **{item['name']}**\n↳ {uses} uses remaining")
        
        if active_items:
            embed.add_field(
                name="__📦 Active Items__",
                value="\n".join(active_items),
                inline=False
            )
        
        if not perks and not active_items:
            embed.description = "Your inventory is empty!"
            
        return embed
    
    async def _update_message(self) -> None:
        """Update both the view and embed of the inventory message."""
        # Create tasks for parallel execution
        tasks = [
            self._create_embed(),
            self._update_options(),
            bank.get_currency_name(self.ctx.guild)  # Get this once for the whole update
        ]
        
        # Wait for all tasks to complete
        embed, _, _ = await asyncio.gather(*tasks)
        
        # Update message with new embed and view
        await self.message.edit(embed=embed, view=self)
    
    async def _handle_activation(self, interaction: discord.Interaction) -> None:
        """Handle item activation.
        
        Args:
            interaction (discord.Interaction): The interaction that triggered this callback
        """
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        try:
            item_id = interaction.data["values"][0].replace("activate_", "")
            item = self.item_registry[item_id]
        except (KeyError, AttributeError):
            await interaction.response.send_message(
                "❌ This item no longer exists!",
                ephemeral=True
            )
            return
        
        # Handle activation based on item type
        if item["type"] == "perk":
            if not item.get("toggleable", False):
                await interaction.response.send_message(
                    "❌ This perk cannot be toggled!",
                    ephemeral=True
                )
                return
                
            if item_id == "notify_ping":
                # Toggle notification status
                async with self.cog.config.member(self.ctx.author).all() as member_data:
                    current_status = member_data.get("notify_on_release", False)
                    member_data["notify_on_release"] = not current_status
                    new_status = member_data["notify_on_release"]
                    self.member_data = member_data
                
                await interaction.response.send_message(
                    f"🔔 Notifications are now {'enabled' if new_status else 'disabled'}",
                    ephemeral=True
                )
                await self._update_message()
            else:
                await interaction.response.send_message(
                    f"✨ Activated {item['emoji']} **{item['name']}**",
                    ephemeral=True
                )
                await self._update_message()
        elif item["type"] == "consumable":
            async with self.cog.config.member(self.ctx.author).all() as member_data:
                # Clean up expired items first
                member_data = await cleanup_inventory(member_data, self.item_registry)
                
                if "active_items" not in member_data:
                    member_data["active_items"] = {}
                
                # Handle jail pass
                if item_id == "jail_pass":
                    # Check if user is in jail
                    if not await self.cog.is_jailed(self.ctx.author):
                        await interaction.response.send_message(
                            "❌ You're not in jail! Save your jail pass for when you need it.",
                            ephemeral=True
                        )
                        return
                    
                    # Use the jail pass
                    if member_data["active_items"][item_id]["uses"] <= 1:
                        del member_data["active_items"][item_id]
                    else:
                        member_data["active_items"][item_id]["uses"] -= 1
                    
                    # Release from jail
                    member_data["jail_until"] = 0
                    member_data["jail_channel"] = None  # Clear jail channel
                    member_data["attempted_jailbreak"] = False  # Reset jailbreak attempt
                    
                    await interaction.response.send_message(
                        "🔑 Used your Get Out of Jail Free card! You are now free.",
                        ephemeral=True
                    )
                    
                    self.member_data = member_data
                    await self._update_message()
                    return
                
                # Handle duration-based items
                if "duration" in item:
                    current_time = int(time.time())
                    
                    # Check if item is already active
                    if item_id in member_data["active_items"]:
                        existing_end = member_data["active_items"][item_id].get("end_time", current_time)
                        if existing_end > current_time:
                            remaining = existing_end - current_time
                            time_str = format_time_remaining(remaining)
                            await interaction.response.send_message(
                                f"❌ This item is already active for {time_str}!",
                                ephemeral=True
                            )
                            return
                    
                    # Activate item with new duration
                    member_data["active_items"][item_id] = {"end_time": current_time + item["duration"]}
                    time_str = format_time_remaining(item["duration"])
                    
                    await interaction.response.send_message(
                        f"✨ Activated {item['emoji']} **{item['name']}** for {time_str}",
                        ephemeral=True
                    )
                # Handle use-based items
                else:
                    current_uses = member_data["active_items"].get(item_id, {}).get("uses", 0)
                    if current_uses <= 0:  # Item not active or no uses left
                        if "uses" in item:  # New item with default uses
                            member_data["active_items"][item_id] = {"uses": item["uses"]}
                            await interaction.response.send_message(
                                f"✨ Added {item['emoji']} **{item['name']}** with {item['uses']} uses",
                                ephemeral=True
                            )
                            self.member_data = member_data
                            await self._update_message()
                            return
                        else:
                            await interaction.response.send_message(
                                "❌ This item has no uses remaining!",
                                ephemeral=True
                            )
                            return
                    
                    # Use the item
                    if current_uses <= 1:
                        del member_data["active_items"][item_id]
                    else:
                        member_data["active_items"][item_id]["uses"] = current_uses - 1
                
                    await interaction.response.send_message(
                        f"✨ Used {item['emoji']} **{item['name']}**" + 
                        (f" ({current_uses-1} uses remaining)" if current_uses > 1 else ""),
                        ephemeral=True
                    )
                
                self.member_data = member_data
                await self._update_message()
    
    async def _handle_sale(self, interaction: discord.Interaction) -> None:
        """Handle item sale.
        
        Args:
            interaction (discord.Interaction): The interaction that triggered this callback
        """
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        try:
            item_id = interaction.data["values"][0].replace("sell_", "")
            item = self.item_registry[item_id]
        except (KeyError, AttributeError):
            await interaction.response.send_message(
                "❌ This item no longer exists!",
                ephemeral=True
            )
            return
        
        # Calculate sell price (25% for perks, 50% for consumables)
        sell_price = int(item["cost"] * (0.25 if item["type"] == "perk" else 0.5))
        currency_name = await bank.get_currency_name(self.ctx.guild)
        
        # Remove item and give credits
        async with self.cog.config.member(self.ctx.author).all() as member_data:
            # Clean up expired items first
            member_data = await cleanup_inventory(member_data, self.item_registry)
            
            if item["type"] == "perk":
                if item_id not in member_data.get("purchased_perks", []):
                    await interaction.response.send_message(
                        "❌ You no longer have this perk!",
                        ephemeral=True
                    )
                    return
                
                member_data["purchased_perks"].remove(item_id)
                
                # Special handling for notify_ping
                if item_id == "notify_ping":
                    member_data["notify_on_release"] = False
                    member_data["notify_unlocked"] = False
            else:
                if item_id not in member_data.get("active_items", {}):
                    await interaction.response.send_message(
                        "❌ You no longer have this item!",
                        ephemeral=True
                    )
                    return
                
                del member_data["active_items"][item_id]
            
            await bank.deposit_credits(self.ctx.author, sell_price)
            self.member_data = member_data
            
            await interaction.response.send_message(
                f"💰 Sold {item['emoji']} **{item['name']}** for {sell_price:,} {currency_name}",
                ephemeral=True
            )
            await self._update_message()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is valid.
        
        Args:
            interaction (discord.Interaction): The interaction to check
            
        Returns:
            bool: True if the interaction is valid, False otherwise
        """
        return interaction.user.id == self.ctx.author.id
    
    async def on_timeout(self) -> None:
        """Handle view timeout by disabling all components."""
        try:
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)
        except (discord.NotFound, discord.HTTPException):
            pass

async def display_inventory(cog: commands.Cog, ctx: commands.Context, item_registry: Dict[str, Dict[str, Any]]) -> None:
    """Display a user's inventory.
    
    This function creates and displays an interactive view that allows users to
    manage their inventory items. Users can activate or sell items through the view.
    
    Args:
        cog (commands.Cog): The cog instance
        ctx (commands.Context): The command context
        item_registry (Dict[str, Dict[str, Any]]): Registry of available items
        
    Note:
        The item_registry should contain items in the following format:
        {
            "item_id": {
                "name": str,
                "description": str,
                "cost": int,
                "type": "consumable" | "perk",
                "emoji": str,
                "can_sell": bool = True,
                "duration": int = None,  # Optional: duration in seconds
                "uses": int = None  # Optional: number of uses
            }
        }
    """
    # Get and clean member data
    member_data = await cog.config.member(ctx.author).all()
    member_data = await cleanup_inventory(member_data, item_registry)
    
    # Save cleaned data
    await cog.config.member(ctx.author).set(member_data)
    
    # Create view and initialize
    view = InventoryView(ctx, cog, member_data, item_registry)
    
    # Create tasks for parallel execution
    tasks = [
        view._create_embed(),
        view._update_options()
    ]
    
    # Wait for all tasks to complete
    embed, _ = await asyncio.gather(*tasks)
    
    # Send message with embed and view
    view.message = await ctx.send(embed=embed, view=view)

def format_time_remaining(seconds: int) -> str:
    """Format remaining time into a human-readable string.
    
    Args:
        seconds (int): Number of seconds remaining
        
    Returns:
        str: Formatted time string (e.g. "2d 5h 30m" or "45m")
    """
    if seconds <= 0:
        return "0m"
        
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or (days > 0 and minutes > 0):  # Show hours if we have days and minutes
        parts.append(f"{hours}h")
    if minutes > 0 or not parts:  # Always show minutes if no larger unit
        parts.append(f"{minutes}m")
    
    return " ".join(parts) 