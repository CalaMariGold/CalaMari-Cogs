"""Base cog for city-related features."""

from redbot.core import commands, bank, Config
from redbot.core.bot import Red
import discord
from datetime import datetime, timezone
import time
from .crime.data import CRIME_TYPES, DEFAULT_GUILD, DEFAULT_MEMBER
import logging

log = logging.getLogger("red")

CONFIG_SCHEMA = {
    "GUILD": {
        "crime_options": {},  # Populated from crime/data.py
        "global_settings": {}  # Populated from crime/data.py
    },
    "MEMBER": {
        "jail_until": 0,  # Timestamp when jail ends
        "last_actions": {},  # Dict of action_type -> last_timestamp
        "total_successful_crimes": 0,
        "total_failed_crimes": 0,
        "total_fines_paid": 0,
        "total_credits_earned": 0,
        "total_stolen_from": 0,  # Credits stolen from others
        "total_stolen_by": 0,  # Credits stolen by others
        "total_bail_paid": 0,  # Amount spent on bail
        "largest_heist": 0,  # Largest successful heist
        "last_target": None  # ID of last targeted user
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
        
    async def send_to_jail(self, member: discord.Member, duration: int):
        """Send a member to jail for specified duration."""
        try:
            current_time = int(time.time())
            await self.config.member(member).jail_until.set(current_time + duration)
            
            # Log jail time
            log.debug(f"Sent {member.display_name} to jail until {current_time + duration}")
        except Exception as e:
            log.error(f"Error sending member to jail: {e}", exc_info=True)
            
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

    async def get_bail_cost(self, guild: discord.Guild, settings: dict) -> int:
        """Calculate bail cost based on settings."""
        try:
            crime_options = await self.config.guild(guild).crime_options()
            
            # Get highest possible fine from enabled crimes
            max_fine = 0
            for crime_data in crime_options.values():
                if not crime_data["enabled"]:
                    continue
                fine = max(0, int(crime_data["max_reward"] * crime_data["fine_multiplier"]))
                max_fine = max(max_fine, fine)
                
            # Bail costs more than the highest fine
            return max(0, int(max_fine * settings["bail_cost_multiplier"]))
        except Exception as e:
            log.error(f"Error calculating bail cost: {e}", exc_info=True)
            return 0
            
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
                log.error(f"Error applying fine: {e}", exc_info=True)
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
                    return 0, _("Target doesn't have enough credits!")
                    
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
                
                return amount, _("🎉 You successfully stole {amount:,} credits from {target}!").format(
                    amount=amount,
                    target=target.display_name
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
                return 0, _("💀 You were caught trying to steal from {target}! You paid a fine of {fine:,} credits and were sent to jail for {minutes}m!").format(
                    target=target.display_name,
                    fine=fine_amount,
                    minutes=crime_data["jail_time"] // 60
                )
            else:
                return 0, _("💀 You were caught and couldn't pay the {fine:,} credit fine! You were sent to jail for {minutes}m!").format(
                    fine=fine_amount,
                    minutes=crime_data["jail_time"] // 60
                )
                
    async def cog_unload(self):
        """Clean up when cog is unloaded."""
        # Cancel any pending tasks
        # Close any open resources
        pass
