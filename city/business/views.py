"""Views for the Business System."""

import discord
from redbot.core import commands, bank
from typing import Optional


class BusinessButton(discord.ui.Button):
    def __init__(self, style: discord.ButtonStyle, label: str, emoji: str, custom_id: str):
        super().__init__(
            style=style, 
            label=label, 
            emoji=emoji, 
            custom_id=custom_id,
            )

class BusinessView(discord.ui.View):
    """View for displaying and managing a user's business."""

    def __init__(self, ctx: commands.Context, cog: commands.Cog) -> None:
        super().__init__(timeout=180)
        self.ctx = ctx
        self.cog = cog
        self.message: Optional[discord.Message] = None

        # Buttons for Business Actions. Include custom IDs.
        self.add_item(BusinessButton(discord.ButtonStyle.primary, "Start Business", "🏢", "start_business"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is valid."""
        return interaction.user.id == self.ctx.author.id

    @discord.ui.button(label="Deposit", style=discord.ButtonStyle.success, custom_id="deposit_button")
    async def deposit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DepositModal(self.cog))

    @discord.ui.button(label="Withdraw", style=discord.ButtonStyle.danger, custom_id="withdraw_button")
    async def withdraw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WithdrawModal(self.cog))

    async def on_timeout(self) -> None:
        """Handle view timeout by disabling all components."""
        try:
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)
        except (discord.NotFound, discord.HTTPException):
            pass

class DepositModal(discord.ui.Modal):
    def __init__(self, cog: commands.Cog):
        super().__init__(title="Deposit Amount")
        self.cog = cog
        self.amount = discord.ui.TextInput(label="Amount", placeholder="Enter the amount to deposit", required=True)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        amount = int(self.amount.value)
        await self.cog.deposit(interaction, amount)

class WithdrawModal(discord.ui.Modal):
    def __init__(self, cog: commands.Cog):
        super().__init__(title="Withdraw Amount")
        self.cog = cog
        self.amount = discord.ui.TextInput(label="Amount", placeholder="Enter the amount to withdraw", required=True)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        amount = int(self.amount.value)
        await self.cog.withdraw(interaction, amount)

async def display_business(cog: commands.Cog, ctx: commands.Context) -> None:
    """Display the business management interface."""
    currency_name = await bank.get_currency_name(ctx.guild)
    vault_balance = await cog.get_vault_balance(ctx.author)
    embed = discord.Embed(
        title="🏢 Business Management",
        description=f"Manage your business operations here.\n\nVault Balance: {vault_balance} {currency_name}",
        color=discord.Color.blue()
    )

    view = BusinessView(ctx, cog)
    view.message = await ctx.send(embed=embed, view=view)
