"""Blackmarket system for the City cog.

This module provides a shop interface for purchasing special items and perks
that can be used to gain advantages in the crime system.

The blackmarket offers both permanent perks and consumable items that can
affect various aspects of the crime system, such as jail time and notifications.
"""

from typing import Dict, Any, Optional
import discord
from redbot.core import bank, commands

# Registry of available blackmarket items
BLACKMARKET_ITEMS: Dict[str, Dict[str, Any]] = {
    "notify_ping": {
        "name": "Jail Release Notification",
        "description": "Get notified when your jail sentence is over",
        "cost": 10000,
        "type": "perk",
        "emoji": "🔔",
        "can_sell": True,
        "toggleable": True
    },
    "jail_reducer": {
        "name": "Reduced Sentence",
        "description": "Permanently reduce jail time by 20%",
        "cost": 20000,
        "type": "perk",
        "emoji": "⚖️",
        "can_sell": True,
        "toggleable": False
    },
    "jail_pass": {
        "name": "Get Out of Jail Free",
        "description": "Instantly escape from jail",
        "cost": 1000,
        "type": "consumable",
        "emoji": "🔑",
        "can_sell": True,
        "uses": 1
    }
}

class BlackmarketView(discord.ui.View):
    """A view for displaying and purchasing items from the blackmarket.
    
    This view provides a shop interface where users can view and purchase
    various items and perks that affect the crime system.
    
    Attributes:
        ctx (commands.Context): The command context
        cog (commands.Cog): The cog instance that created this view
        message (Optional[discord.Message]): The message containing this view
    """
    
    def __init__(self, ctx: commands.Context, cog: commands.Cog) -> None:
        super().__init__(timeout=180)
        self.ctx = ctx
        self.cog = cog
        self.message: Optional[discord.Message] = None
        self._update_options()
    
    def _update_options(self) -> None:
        """Update the select menu options based on available items."""
        # Clear existing options
        for child in self.children[:]:
            self.remove_item(child)
        
        # Create select menu
        select = discord.ui.Select(
            placeholder="Select an item to purchase",
            options=[
                discord.SelectOption(
                    label=item["name"],
                    value=item_id,
                    description=f"{item['description']} - {item['cost']:,} credits",
                    emoji=item["emoji"]
                )
                for item_id, item in BLACKMARKET_ITEMS.items()
            ]
        )
        select.callback = self._handle_purchase
        self.add_item(select)
    
    async def _handle_purchase(self, interaction: discord.Interaction) -> None:
        """Handle item purchase.
        
        Args:
            interaction (discord.Interaction): The interaction that triggered this callback
        """
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
        
        try:
            item_id = interaction.data["values"][0]
            item = BLACKMARKET_ITEMS[item_id]
        except (KeyError, AttributeError):
            await interaction.response.send_message(
                "❌ This item is no longer available!",
                ephemeral=True
            )
            return
        
        # Check if user can afford
        balance = await bank.get_balance(self.ctx.author)
        if balance < item["cost"]:
            currency_name = await bank.get_currency_name(self.ctx.guild)
            await interaction.response.send_message(
                f"❌ You need {item['cost']:,} {currency_name} to buy this!",
                ephemeral=True
            )
            return
        
        # Handle purchase
        async with self.cog.config.member(self.ctx.author).all() as member_data:
            if item["type"] == "perk":
                if item_id in member_data.get("purchased_perks", []):
                    await interaction.response.send_message(
                        "❌ You already own this perk!",
                        ephemeral=True
                    )
                    return
                
                if "purchased_perks" not in member_data:
                    member_data["purchased_perks"] = []
                member_data["purchased_perks"].append(item_id)
                
                # Special handling for notify_ping
                if item_id == "notify_ping":
                    member_data["notify_unlocked"] = True
                    member_data["notify_on_release"] = True
            else:  # consumable
                if "active_items" not in member_data:
                    member_data["active_items"] = {}
                
                if item_id in member_data["active_items"]:
                    current_uses = member_data["active_items"][item_id].get("uses", 0)
                    if current_uses > 0:
                        await interaction.response.send_message(
                            "❌ You already have this item with uses remaining!",
                            ephemeral=True
                        )
                        return
                
                member_data["active_items"][item_id] = {"uses": item["uses"]}
        
        # Complete purchase
        await bank.withdraw_credits(self.ctx.author, item["cost"])
        currency_name = await bank.get_currency_name(self.ctx.guild)
        
        await interaction.response.send_message(
            f"✅ Purchased {item['emoji']} **{item['name']}** for {item['cost']:,} {currency_name}",
            ephemeral=True
        )
    
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

async def display_blackmarket(cog: commands.Cog, ctx: commands.Context) -> None:
    """Display the blackmarket shop interface.
    
    Args:
        cog (commands.Cog): The cog instance
        ctx (commands.Context): The command context
    """
    currency_name = await bank.get_currency_name(ctx.guild)
    
    # Create embed
    embed = discord.Embed(
        title="🏴‍☠️ Black Market",
        description="Welcome to the black market! Here you can purchase special items and perks.",
        color=discord.Color.dark_red()
    )
    
    # Add perks section
    perks = []
    for item_id, item in BLACKMARKET_ITEMS.items():
        if item["type"] == "perk":
            perks.append(f"{item['emoji']} **{item['name']}** - {item['cost']:,} {currency_name}\n"
                        f"↳ {item['description']}")
    
    if perks:
        embed.add_field(
            name="__🔒 Permanent Perks__",
            value="\n".join(perks),
            inline=False
        )
    
    # Add consumable items section
    items = []
    for item_id, item in BLACKMARKET_ITEMS.items():
        if item["type"] == "consumable":
            items.append(f"{item['emoji']} **{item['name']}** - {item['cost']:,} {currency_name}\n"
                        f"↳ {item['description']}")
    
    if items:
        embed.add_field(
            name="__📦 Consumable Items__",
            value="\n".join(items),
            inline=False
        )
    
    # Create and send view
    view = BlackmarketView(ctx, cog)
    view.message = await ctx.send(embed=embed, view=view) 