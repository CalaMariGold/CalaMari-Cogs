"""Base cog for city-related features."""

from redbot.core import commands, bank, Config
from redbot.core.bot import Red
import discord
from datetime import datetime, timezone
import time
from .crime.data import CRIME_TYPES, DEFAULT_GUILD, DEFAULT_MEMBER

CONFIG_SCHEMA = {
    "GUILD": {
        "crime_options": {},  # Crime configuration from crime/data.py
        "global_settings": {},  # Global settings from crime/data.py including:
                             # - Jail and bail settings
                             # - Crime targeting rules
                             # - Notification settings (cost and toggle)
        "blackmarket_items": {}  # Blackmarket items configuration
    },
    "MEMBER": {
        "jail_until": 0,  # Unix timestamp when jail sentence ends
        "last_actions": {},  # Dict mapping action_type -> last_timestamp
        "total_successful_crimes": 0,  # Total number of successful crimes
        "total_failed_crimes": 0,  # Total number of failed crimes
        "total_fines_paid": 0,  # Total amount paid in fines
        "total_credits_earned": 0,  # Total credits earned from all sources
        "total_stolen_from": 0,  # Credits stolen from other users
        "total_stolen_by": 0,  # Credits stolen by other users
        "total_bail_paid": 0,  # Total amount spent on bail
        "largest_heist": 0,  # Largest successful heist amount
        "last_target": None,  # ID of last targeted user (anti-farming)
        "notify_unlocked": False,  # Whether notifications feature is unlocked
        "notify_on_release": False,  # Whether notifications are currently enabled
        "jail_channel": None,  # ID of channel where user was jailed (for notifications)
        "attempted_jailbreak": False,  # Whether user attempted jailbreak this sentence
        "purchased_perks": [],  # List of permanent perks owned from blackmarket
        "active_items": {}  # Dict of temporary items with expiry timestamps or uses
    }
}

class CityBase:
    """Base class for city-related features."""
    
    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=95932766180343808,
            force_registration=True
        )
        
        # Register defaults - combine CONFIG_SCHEMA and crime defaults
        guild_defaults = {**CONFIG_SCHEMA["GUILD"], **DEFAULT_GUILD}
        member_defaults = {**CONFIG_SCHEMA["MEMBER"], **DEFAULT_MEMBER}
        
        self.config.register_guild(**guild_defaults)
        self.config.register_member(**member_defaults)
        
        # Config schema version
        self.CONFIG_SCHEMA = 3
        
        # Track active tasks
        self.tasks = []
        
    async def red_delete_data_for_user(self, *, requester, user_id: int):
        """Delete user data when requested."""
        # Delete member data
        await self.config.member_from_ids(None, user_id).clear()
        
        # Remove user from other members' last_target
        all_members = await self.config.all_members()
        for guild_id, guild_data in all_members.items():
            for member_id, member_data in guild_data.items():
                if member_data.get("last_target") == user_id:
                    await self.config.member_from_ids(guild_id, member_id).last_target.set(None)
                    
    async def get_jail_time_remaining(self, member: discord.Member) -> int:
        """Get remaining jail time in seconds."""
        jail_until = await self.config.member(member).jail_until()
        if not jail_until:
            return 0
            
        current_time = int(time.time())
        remaining = max(0, jail_until - current_time)
        
        # Clear jail if time is up
        if remaining == 0 and jail_until != 0:
            await self.config.member(member).jail_until.set(0)
            
        return remaining
        
    async def get_remaining_cooldown(self, member: discord.Member, action_type: str) -> int:
        """Get remaining cooldown time for an action."""
        current_time = int(time.time())
        last_actions = await self.config.member(member).last_actions()
        
        # Get last attempt time and cooldown
        last_attempt = last_actions.get(action_type, 0)
        if not last_attempt:
            return 0
            
        # Get crime data for cooldown duration
        crime_options = await self.config.guild(member.guild).crime_options()
        if action_type not in crime_options:
            return 0
            
        cooldown = crime_options[action_type]["cooldown"]
        remaining = max(0, cooldown - (current_time - last_attempt))
        
        return remaining
        
    async def set_action_cooldown(self, member: discord.Member, action_type: str):
        """Set cooldown for an action."""
        current_time = int(time.time())
        async with self.config.member(member).last_actions() as last_actions:
            last_actions[action_type] = current_time
            
    async def is_jailed(self, member: discord.Member) -> bool:
        """Check if a member is currently jailed."""
        remaining = await self.get_jail_time_remaining(member)
        return remaining > 0

    async def apply_fine(self, member: discord.Member, crime_type: str, crime_data: dict) -> tuple[bool, int]:
        """Apply a fine to a user. Returns (paid_successfully, amount)."""
        fine_amount = int(crime_data["max_reward"] * crime_data["fine_multiplier"])
        
        try:
            # Try to take full fine
            await bank.withdraw_credits(member, fine_amount)
            
            # Update stats
            async with self.config.member(member).all() as member_data:
                member_data["total_fines_paid"] += fine_amount
            
            return True, fine_amount
        except ValueError:
            # If they can't pay full fine, take what they have
            try:
                balance = await bank.get_balance(member)
                if balance > 0:
                    await bank.withdraw_credits(member, balance)
                    
                    # Update stats with partial payment
                    async with self.config.member(member).all() as member_data:
                        member_data["total_fines_paid"] += balance
                        
                return False, fine_amount
            except Exception as e:
                return False, fine_amount
                
    async def handle_target_crime(
        self,
        member: discord.Member,
        target: discord.Member,
        crime_data: dict,
        success: bool
    ) -> tuple[int, str]:
        """Handle a targeted crime attempt. Returns (amount, message)."""
        settings = await self.config.guild(member.guild).global_settings()
        
        if success:
            # Calculate amount to steal
            amount = await calculate_stolen_amount(target, crime_data, settings)
            
            try:
                # Check target's balance first
                target_balance = await bank.get_balance(target)
                if target_balance < amount:
                    return 0, _("Target doesn't have enough {currency}!").format(currency=await bank.get_currency_name(target.guild))
                    
                # Perform the transfer atomically
                await bank.withdraw_credits(target, amount)
                await bank.deposit_credits(member, amount)
                
                # Update stats only after successful transfer
                async with self.config.member(member).all() as member_data:
                    member_data["total_stolen_from"] += amount
                    member_data["total_credits_earned"] += amount
                    member_data["last_target"] = target.id
                    if amount > member_data["largest_heist"]:
                        member_data["largest_heist"] = amount
                        
                async with self.config.member(target).all() as target_data:
                    target_data["total_stolen_by"] += amount
                
                return amount, _("🎉 You successfully stole {amount:,} {currency} from {target}!").format(
                    amount=amount,
                    target=target.mention,
                    currency=await bank.get_currency_name(target.guild)
                )
            except ValueError as e:
                return 0, _("Failed to steal credits: Balance changed!")
        else:
            # Failed attempt
            fine_paid, fine_amount = await self.apply_fine(member, crime_data["crime_type"], crime_data)
            
            # Update stats
            async with self.config.member(member).all() as member_data:
                member_data["total_failed_crimes"] += 1
            
            if fine_paid:
                return 0, _("💀 You were caught trying to steal from {target}! You paid a fine of {fine:,} {currency} and were sent to jail for {minutes}m!").format(
                    target=target.display_name,
                    fine=fine_amount,
                    minutes=crime_data["jail_time"] // 60,
                    currency=await bank.get_currency_name(target.guild)
                )
            else:
                return 0, _("💀 You were caught and couldn't pay the {fine:,} credit fine! You were sent to jail for {minutes}m!").format(
                    fine=fine_amount,
                    minutes=crime_data["jail_time"] // 60
                )
                
    async def cog_unload(self):
        """Clean up when cog is unloaded."""
        for task in self.tasks:
            task.cancel()
    class ConfirmWipeView(discord.ui.View):
        def __init__(self, ctx: commands.Context, user: discord.Member):
            super().__init__(timeout=30.0)  # 30 second timeout
            self.ctx = ctx
            self.user = user
            self.value = None

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            # Only allow the original command author to use the buttons
            return interaction.user.id == self.ctx.author.id

        @discord.ui.button(label='Confirm Wipe', style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = True
            self.stop()
            # Disable all buttons after clicking
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)

        @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = False
            self.stop()
            # Disable all buttons after clicking
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)

        async def on_timeout(self):
            # Disable all buttons if the view times out
            for item in self.children:
                item.disabled = True
            # Try to update the message with disabled buttons
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    class ConfirmGlobalWipeView(discord.ui.View):
        def __init__(self, ctx: commands.Context):
            super().__init__(timeout=30.0)  # 30 second timeout
            self.ctx = ctx
            self.value = None
            self.confirmation_phrase = None
            self.waiting_for_confirmation = False

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            # Only allow the original command author to use the buttons
            return interaction.user.id == self.ctx.author.id

        @discord.ui.button(label='I Understand - Proceed to Confirmation', style=discord.ButtonStyle.danger)
        async def confirm_understanding(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.waiting_for_confirmation:
                return
                
            self.waiting_for_confirmation = True
            
            # Generate a random confirmation phrase
            import random
            import string
            import asyncio
            self.confirmation_phrase = ''.join(random.choices(string.ascii_uppercase, k=6))
            
            # Disable the initial button
            button.disabled = True
            # Remove the cancel button if it exists
            cancel_button = discord.utils.get(self.children, label='Cancel')
            if cancel_button:
                self.remove_item(cancel_button)
            
            # Add the final confirmation button
            confirm_button = discord.ui.Button(
                label=f'CONFIRM WIPE - Type "{self.confirmation_phrase}"',
                style=discord.ButtonStyle.danger,
                disabled=True,
                custom_id='final_confirm'
            )
            self.add_item(confirm_button)
            
            await interaction.response.edit_message(
                content=f"⚠️ **FINAL WARNING**\n\n"
                f"To proceed with wiping ALL city data for ALL users, you must type:\n"
                f"```\n{self.confirmation_phrase}\n```\n"
                f"This will permanently delete all user stats, crime records, and other city data.\n"
                f"You have 30 seconds to confirm.",
                view=self
            )
            
            # Start listening for the confirmation message
            def check(m):
                return (m.author.id == self.ctx.author.id and 
                       m.channel.id == self.ctx.channel.id and 
                       m.content == self.confirmation_phrase)
            
            try:
                await self.ctx.bot.wait_for('message', timeout=30.0, check=check)
                self.value = True
            except asyncio.TimeoutError:
                self.value = None
            finally:
                self.stop()
                # Try to update the message one last time
                try:
                    for item in self.children:
                        item.disabled = True
                    await self.message.edit(view=self)
                except (discord.NotFound, discord.HTTPException):
                    pass

        @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.waiting_for_confirmation:
                return
                
            self.value = False
            self.stop()
            # Disable all buttons after clicking
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)

        async def on_timeout(self):
            self.value = None
            # Disable all buttons if the view times out
            for item in self.children:
                item.disabled = True
            # Try to update the message with disabled buttons
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    @commands.command()
    @commands.is_owner()
    async def wipecitydata(self, ctx: commands.Context, user: discord.Member):
        """Wipe all city-related data for a specific user.
        
        This will remove all their stats, including:
        - Crime records and cooldowns
        - Jail status and history
        - All statistics (successful crimes, failed crimes, etc.)
        - References in other users' data
        
        This action cannot be undone.
        
        Parameters
        ----------
        user: discord.Member
            The user whose data should be wiped
        """
        # Create confirmation view
        view = self.ConfirmWipeView(ctx, user)
        view.message = await ctx.send(
            f"⚠️ Are you sure you want to wipe all city data for {user.display_name}?\n"
            "This action cannot be undone and will remove all their stats, including:\n"
            "• Crime records and cooldowns\n"
            "• Jail status and history\n"
            "• All statistics (successful crimes, failed crimes, etc.)\n"
            "• References in other users' data",
            view=view
        )

        # Wait for the user's response
        await view.wait()

        if view.value is None:
            await ctx.send("❌ Wipe cancelled - timed out.")
            return
        elif view.value is False:
            await ctx.send("❌ Wipe cancelled.")
            return

        try:
            # Step 1: Clear all member data across all guilds
            all_guilds = self.bot.guilds
            for guild in all_guilds:
                await self.config.member_from_ids(guild.id, user.id).clear()
            
            # Step 2: Remove user from other members' data
            all_members = await self.config.all_members()
            for guild_id, guild_data in all_members.items():
                for member_id, member_data in guild_data.items():
                    if member_id == user.id:
                        continue  # Skip the user's own data as it's already cleared
                        
                    modified = False
                    # Check last_target
                    if member_data.get("last_target") == user.id:
                        await self.config.member_from_ids(guild_id, member_id).last_target.set(None)
                        modified = True
                    
                    # If we add any other cross-user references in the future,
                    # they should be cleaned up here
            
            await ctx.send(f"✅ Successfully wiped all city data for {user.display_name} across all guilds.")
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred while wiping data: {str(e)}")

    @commands.command()
    @commands.is_owner()
    async def wipecityallusers(self, ctx: commands.Context):
        """Wipe ALL city-related data for ALL users.
        
        This is an extremely destructive action that will:
        - Delete ALL user stats
        - Remove ALL crime records and cooldowns
        - Clear ALL jail status and history
        - Wipe ALL cross-user references
        - Remove ALL data across ALL guilds
        
        This action absolutely cannot be undone.
        """
        # Create confirmation view
        view = self.ConfirmGlobalWipeView(ctx)
        view.message = await ctx.send(
            "🚨 **GLOBAL CITY DATA WIPE** 🚨\n\n"
            "You are about to wipe ALL city data for ALL users across ALL guilds.\n\n"
            "This will permanently delete:\n"
            "• All user statistics\n"
            "• All crime records and cooldowns\n"
            "• All jail records and history\n"
            "• All cross-user references\n"
            "• All other city-related data\n\n"
            "This action CANNOT be undone and will affect ALL users.\n"
            "Are you sure you want to proceed?",
            view=view
        )

        # Wait for the user's response
        await view.wait()

        if view.value is None:
            await ctx.send("❌ Global wipe cancelled - timed out.")
            return
        elif view.value is False:
            await ctx.send("❌ Global wipe cancelled.")
            return

        try:
            # Step 1: Clear all member data across all guilds
            all_members = await self.config.all_members()
            count = 0
            for guild_id, guild_data in all_members.items():
                for member_id in guild_data.keys():
                    await self.config.member_from_ids(guild_id, member_id).clear()
                    count += 1
            
            # Step 2: Clear all guild settings to defaults
            guild_count = 0
            all_guilds = self.bot.guilds
            for guild in all_guilds:
                await self.config.guild(guild).clear()
                guild_count += 1
                
            await ctx.send(f"✅ Successfully wiped ALL city data:\n"
                         f"• Cleared data for {count:,} users\n"
                         f"• Reset settings in {guild_count:,} guilds")
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred while wiping data: {str(e)}")
