"""Commands for the Business module of the City cog."""

import discord
import asyncio
from redbot.core import commands, Config, bank
from .views import display_business

class Business(commands.Cog):
    """Business Commands."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_member(vault_balance=0, business_level=1)
        self.profit_task = self.bot.loop.create_task(self.distribute_profits())

    async def distribute_profits(self):
        """Calculate and distribute profits based on vault balance and business level."""
        # As an example, this task will run every hour and distribute profits to all users with a vault balance. 
        # The profit rate is 2% base rate, plus 0.5% per business level.
        # This is a simple example and can be expanded upon, currently user Config will init a level 1 business for all users.
        while True:
            await asyncio.sleep(3600)  # Wait for 1 hour
            all_members = await self.config.all_members()
            for member_id, data in all_members.items():
                vault_balance = data.get("vault_balance", 0)
                business_level = data.get("business_level", 1)
                daily_rate = 0.02 + (business_level - 1) * 0.005  # 2% base rate, +0.5% per level
                hourly_profit = vault_balance * (daily_rate / 24)
                async with self.config.member_from_ids(None, member_id).vault_balance() as balance:
                    balance += hourly_profit

    @commands.group(name="business", invoke_without_command=True)
    async def business(self, ctx: commands.Context):
        """Open the main business menu."""
        await display_business(self, ctx)

    @business.command(name="start")
    async def start_business(self, ctx: commands.Context, name: str, industry: str):
        """Start a new business."""
        await ctx.send(f"Starting a new business: {name} in the {industry} industry.")

    @business.command(name="deposit")
    async def deposit(self, interaction: discord.Interaction, amount: int):
        """Handle deposit action."""
        try:
            if amount <= 0:
                await interaction.response.send_message("Amount must be positive.", ephemeral=True)
                return
            if not await bank.can_spend(interaction.user, amount):
                await interaction.response.send_message("You don't have enough credits.", ephemeral=True)
                return
            await bank.withdraw_credits(interaction.user, amount)
            balance = await self.config.member(interaction.user).vault_balance()
            new_balance = balance + amount
            await self.config.member(interaction.user).vault_balance.set(new_balance)
            currency_name = await bank.get_currency_name(interaction.guild)
            await interaction.response.send_message(f"Deposited {amount} {currency_name} to your business vault.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Something went wrong: {str(e)}", ephemeral=True)

    @business.command(name="withdraw")
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        """Handle withdraw action."""
        try:
            if amount <= 0:
                await interaction.response.send_message("Amount must be positive.", ephemeral=True)
                return
            balance = await self.config.member(interaction.user).vault_balance()
            if amount > balance:
                await interaction.response.send_message("You don't have enough credits in your vault.", ephemeral=True)
                return
            new_balance = balance - amount
            await self.config.member(interaction.user).vault_balance.set(new_balance)
            await bank.deposit_credits(interaction.user, amount)
            currency_name = await bank.get_currency_name(interaction.guild)
            await interaction.response.send_message(f"Withdrew {amount} {currency_name} from your business vault.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Something went wrong: {str(e)}", ephemeral=True)

    @business.command(name="initvault")
    async def init_vault(self, ctx: commands.Context):
        """Initialize the vault balance for the user."""
        await self.config.member(ctx.author).vault_balance.set(0)
        await ctx.send("Vault balance initialized.")

    async def get_vault_balance(self, user: discord.Member) -> int:
        """Get the current vault balance for a user."""
        return await self.config.member(user).vault_balance()
