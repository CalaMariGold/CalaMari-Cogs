"""Jail management system for the City cog.


CURRENTLY NOT IN USE AND WIP

"""
from typing import Optional, Dict, Any, Tuple, List
import time
import asyncio
import random
import discord
from redbot.core import Config, bank
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.i18n import Translator
from .scenarios import get_random_jailbreak_scenario

_ = Translator("City", __file__)

class JailException(Exception):
    """Base exception for jail-related errors."""
    pass

class JailStateError(JailException):
    """Raised when there's an error with jail state management."""
    pass

class JailNotificationError(JailException):
    """Raised when there's an error with jail notifications."""
    pass

class BailError(JailException):
    """Raised when there's an error with bail operations."""
    pass

class JailbreakError(JailException):
    """Raised when there's an error with jailbreak operations."""
    pass

class PerkError(JailException):
    """Raised when there's an error with perk operations."""
    pass

class PerkManager:
    """Manages jail-related perks."""
    
    def __init__(self, config: Config):
        self.config = config
        
    async def has_perk(self, member: discord.Member, perk_name: str) -> bool:
        """Check if a member has a specific perk."""
        try:
            member_data = await self.config.member(member).all()
            return perk_name in member_data.get("purchased_perks", [])
        except Exception as e:
            raise PerkError(f"Failed to check perk status: {str(e)}")
            
    async def apply_sentence_reduction(self, member: discord.Member, jail_time: int) -> int:
        """Apply sentence reduction if member has the jail_reducer perk."""
        try:
            if await self.has_perk(member, "jail_reducer"):
                return int(jail_time * 0.8)  # 20% reduction
            return jail_time
        except Exception as e:
            raise PerkError(f"Failed to apply sentence reduction: {str(e)}")
            
    async def should_notify(self, member: discord.Member) -> bool:
        """Check if member should receive jail notifications."""
        try:
            member_data = await self.config.member(member).all()
            has_notifier = await self.has_perk(member, "jail_notifier")
            notify_enabled = member_data.get("notify_on_release", False)
            return has_notifier and notify_enabled
        except Exception as e:
            raise PerkError(f"Failed to check notification status: {str(e)}")
            
    async def toggle_notifications(self, member: discord.Member) -> bool:
        """Toggle jail release notifications for a member."""
        try:
            if not await self.has_perk(member, "jail_notifier"):
                raise PerkError("You don't have the jail notifier perk!")
                
            async with self.config.member(member).all() as member_data:
                current = member_data.get("notify_on_release", False)
                member_data["notify_on_release"] = not current
                return not current
        except Exception as e:
            raise PerkError(f"Failed to toggle notifications: {str(e)}")

class JailbreakScenario:
    """Represents a jailbreak attempt scenario."""
    
    def __init__(self, data: Dict[str, Any]):
        self.name = data["name"]
        self.attempt_text = data["attempt_text"]
        self.success_text = data["success_text"]
        self.fail_text = data["fail_text"]
        self.base_chance = data["base_chance"]
        self.events = data["events"]

    @property
    def random_events(self) -> List[Dict[str, Any]]:
        """Get 1-3 random events for this scenario."""
        num_events = random.randint(1, 3)
        return random.sample(self.events, num_events)

    def format_text(self, text: str, **kwargs) -> str:
        """Format scenario text with given parameters."""
        return _(text).format(**kwargs)

class JailManager:
    """Manages all jail-related functionality."""
    
    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config
        self.notification_tasks: Dict[int, asyncio.Task] = {}  # member_id: task
        self.perk_manager = PerkManager(config)
        
    async def get_jail_state(self, member: discord.Member) -> Dict[str, Any]:
        """Get the complete jail state for a member."""
        try:
            member_data = await self.config.member(member).all()
            return {
                "jail_until": member_data.get("jail_until", 0),
                "attempted_jailbreak": member_data.get("attempted_jailbreak", False),
                "jail_channel": member_data.get("jail_channel", None),
                "notify_on_release": member_data.get("notify_on_release", False),
                "reduced_sentence": "jail_reducer" in member_data.get("purchased_perks", []),
                "original_sentence": member_data.get("original_sentence", 0)
            }
        except Exception as e:
            raise JailStateError(f"Failed to get jail state: {str(e)}")

    async def update_jail_state(self, member: discord.Member, state: Dict[str, Any]) -> None:
        """Update the jail state for a member."""
        try:
            async with self.config.member(member).all() as member_data:
                member_data["jail_until"] = state.get("jail_until", member_data.get("jail_until", 0))
                member_data["attempted_jailbreak"] = state.get("attempted_jailbreak", member_data.get("attempted_jailbreak", False))
                member_data["jail_channel"] = state.get("jail_channel", member_data.get("jail_channel", None))
                member_data["notify_on_release"] = state.get("notify_on_release", member_data.get("notify_on_release", False))
                member_data["original_sentence"] = state.get("original_sentence", member_data.get("original_sentence", 0))
        except Exception as e:
            raise JailStateError(f"Failed to update jail state: {str(e)}")

    async def get_jail_time_remaining(self, member: discord.Member) -> int:
        """Get remaining jail time in seconds."""
        try:
            state = await self.get_jail_state(member)
            jail_until = state["jail_until"]
            
            if not jail_until:
                return 0
                
            current_time = int(time.time())
            remaining = max(0, jail_until - current_time)
            
            # Clear jail if time is up
            if remaining == 0 and jail_until != 0:
                await self.clear_jail_state(member)
                
            return remaining
        except Exception as e:
            raise JailStateError(f"Failed to get remaining jail time: {str(e)}")

    async def send_to_jail(self, member: discord.Member, jail_time: int, channel: Optional[discord.TextChannel] = None) -> None:
        """Send a member to jail."""
        try:
            # Get current state
            state = await self.get_jail_state(member)
            original_time = jail_time

            # Apply sentence reduction if they have the perk
            jail_time = await self.perk_manager.apply_sentence_reduction(member, jail_time)

            # Update state
            new_state = {
                "jail_until": int(time.time()) + jail_time,
                "attempted_jailbreak": False,  # Reset on new sentence
                "jail_channel": channel.id if channel else None,
                "original_sentence": original_time
            }
            await self.update_jail_state(member, new_state)

            # Handle notification scheduling
            if await self.perk_manager.should_notify(member):
                await self._schedule_release_notification(member, jail_time, channel)

        except Exception as e:
            raise JailStateError(f"Failed to send member to jail: {str(e)}")

    async def clear_jail_state(self, member: discord.Member) -> None:
        """Clear all jail-related state for a member."""
        try:
            # Cancel any pending notifications
            await self._cancel_notification(member)
            
            # Clear jail state
            await self.update_jail_state(member, {
                "jail_until": 0,
                "attempted_jailbreak": False,
                "jail_channel": None,
                "original_sentence": 0
            })
        except Exception as e:
            raise JailStateError(f"Failed to clear jail state: {str(e)}")

    async def _schedule_release_notification(self, member: discord.Member, jail_time: int, channel: Optional[discord.TextChannel] = None) -> None:
        """Schedule a notification for when a member's jail sentence is over."""
        try:
            # Cancel any existing notification
            await self._cancel_notification(member)
            
            # Create new notification task
            task = asyncio.create_task(self._notification_handler(member, jail_time, channel))
            self.notification_tasks[member.id] = task
            
        except Exception as e:
            raise JailNotificationError(f"Failed to schedule release notification: {str(e)}")

    async def _cancel_notification(self, member: discord.Member) -> None:
        """Cancel a pending release notification."""
        try:
            if member.id in self.notification_tasks:
                self.notification_tasks[member.id].cancel()
                del self.notification_tasks[member.id]
        except Exception as e:
            raise JailNotificationError(f"Failed to cancel notification: {str(e)}")

    async def _notification_handler(self, member: discord.Member, jail_time: int, channel: Optional[discord.TextChannel] = None) -> None:
        """Handle the notification process for jail release."""
        try:
            await asyncio.sleep(jail_time)
            
            # Verify they're actually out (in case sentence was extended)
            remaining = await self.get_jail_time_remaining(member)
            if remaining <= 0:
                state = await self.get_jail_state(member)
                if state["notify_on_release"]:
                    await self._send_notification(member, channel)
        except asyncio.CancelledError:
            pass  # Task was cancelled, ignore
        except Exception as e:
            raise JailNotificationError(f"Notification handler failed: {str(e)}")

    async def _send_notification(self, member: discord.Member, channel: Optional[discord.TextChannel] = None) -> None:
        """Send the actual notification message."""
        try:
            message = f"🔔 {member.mention} Your jail sentence is over! You're now free to commit crimes again."
            
            if channel:
                await channel.send(message)
            else:
                try:
                    await member.send(message)
                except (discord.Forbidden, discord.HTTPException):
                    pass  # Can't DM the user, silently fail
        except Exception as e:
            raise JailNotificationError(f"Failed to send notification: {str(e)}")

    def is_in_jail(self, member: discord.Member) -> bool:
        """Quick check if a member is currently in jail."""
        return self.get_jail_time_remaining(member) > 0

    async def calculate_bail_cost(self, member: discord.Member) -> Tuple[int, float]:
        """Calculate bail cost based on remaining jail time.
        
        Returns:
            Tuple[int, float]: (bail_cost, multiplier)
        """
        try:
            # Get remaining time and settings
            remaining_time = await self.get_jail_time_remaining(member)
            if remaining_time <= 0:
                raise BailError("Member is not in jail")

            settings = await self.config.guild(member.guild).global_settings()
            multiplier = float(settings.get("bail_cost_multiplier", 1.5))
            
            # Calculate cost (remaining minutes * multiplier)
            bail_cost = int(multiplier * (remaining_time / 60))  # Convert seconds to minutes
            
            return bail_cost, multiplier
            
        except Exception as e:
            raise BailError(f"Failed to calculate bail cost: {str(e)}")

    async def can_pay_bail(self, member: discord.Member) -> Tuple[bool, int, str]:
        """Check if a member can pay bail.
        
        Returns:
            Tuple[bool, int, str]: (can_pay, cost, currency_name)
        """
        try:
            # Check if bail is allowed
            settings = await self.config.guild(member.guild).global_settings()
            if not settings.get("allow_bail", True):
                raise BailError("Bail is not allowed in this server")

            # Calculate bail cost
            bail_cost, _ = await self.calculate_bail_cost(member)
            
            # Get currency info
            currency_name = await bank.get_currency_name(member.guild)
            can_pay = await bank.can_spend(member, bail_cost)
            
            return can_pay, bail_cost, currency_name
            
        except Exception as e:
            raise BailError(f"Failed to check bail payment: {str(e)}")

    async def process_bail_payment(self, member: discord.Member) -> Tuple[int, int, str]:
        """Process bail payment and release from jail.
        
        Returns:
            Tuple[int, int, str]: (bail_cost, new_balance, currency_name)
        """
        try:
            # Verify they can pay
            can_pay, bail_cost, currency_name = await self.can_pay_bail(member)
            if not can_pay:
                raise BailError(f"Insufficient funds to pay {bail_cost} {currency_name}")

            # Process payment
            await bank.withdraw_credits(member, bail_cost)
            new_balance = await bank.get_balance(member)

            # Update stats
            async with self.config.member(member).all() as member_data:
                member_data["total_bail_paid"] = member_data.get("total_bail_paid", 0) + bail_cost

            # Release from jail
            await self.clear_jail_state(member)

            return bail_cost, new_balance, currency_name

        except Exception as e:
            raise BailError(f"Failed to process bail payment: {str(e)}")

    async def format_bail_embed(self, member: discord.Member) -> discord.Embed:
        """Format bail information into an embed."""
        try:
            # Get bail information
            remaining_time = await self.get_jail_time_remaining(member)
            bail_cost, multiplier = await self.calculate_bail_cost(member)
            current_balance = await bank.get_balance(member)
            currency_name = await bank.get_currency_name(member.guild)
            
            # Get member data for perk check
            state = await self.get_jail_state(member)
            
            # Create embed
            embed = discord.Embed(
                title="💰 Bail Payment Available",
                description=(
                    "You can pay bail to get out of jail immediately, or wait out your sentence.\n\n"
                    f"**Time Remaining:** {self._format_time(remaining_time)}"
                    + (" (Reduced by 20%)" if state["reduced_sentence"] else "") + "\n"
                    f"**Bail Cost:** {bail_cost:,} {currency_name}\n"
                    f"**Current Balance:** {current_balance:,} {currency_name}\n\n"
                    f"*Bail cost is calculated as: remaining minutes × {multiplier}*"
                ),
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Requested by {member.display_name}", icon_url=member.display_avatar.url)
            
            return embed
            
        except Exception as e:
            raise BailError(f"Failed to format bail embed: {str(e)}")

    def _format_time(self, seconds: int) -> str:
        """Format seconds into a human-readable string."""
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"

    async def get_jailbreak_scenario(self) -> JailbreakScenario:
        """Get a random jailbreak scenario."""
        try:
            # Get scenario from scenarios.py
            scenario_data = get_random_jailbreak_scenario()
            return JailbreakScenario(scenario_data)
        except Exception as e:
            raise JailbreakError(f"Failed to get jailbreak scenario: {str(e)}")

    async def process_jailbreak_attempt(self, member: discord.Member, channel: discord.TextChannel) -> Tuple[bool, discord.Embed, List[str]]:
        """Process a jailbreak attempt.
        
        Returns:
            Tuple[bool, discord.Embed, List[str]]: (success, result_embed, event_messages)
        """
        try:
            # Verify member is in jail
            if not await self.is_in_jail(member):
                raise JailbreakError("Member is not in jail")

            # Check if already attempted
            state = await self.get_jail_state(member)
            if state["attempted_jailbreak"]:
                raise JailbreakError("Already attempted jailbreak this sentence")

            # Mark attempt
            await self.update_jail_state(member, {"attempted_jailbreak": True})

            # Get scenario and process events
            scenario = await self.get_jailbreak_scenario()
            success_chance = scenario.base_chance
            event_messages = []
            
            # Process random events
            for event in scenario.random_events:
                event_text = event["text"]
                currency_name = await bank.get_currency_name(member.guild)
                event_text = event_text.format(currency=currency_name)
                
                # Apply chance modifiers
                if "chance_bonus" in event:
                    success_chance = min(1.0, success_chance + event["chance_bonus"])
                elif "chance_penalty" in event:
                    success_chance = max(0.05, success_chance - event["chance_penalty"])
                
                # Apply currency effects
                if "currency_bonus" in event:
                    await bank.deposit_credits(member, event["currency_bonus"])
                    event_text += f" (+{event['currency_bonus']} {currency_name})"
                elif "currency_penalty" in event:
                    await bank.withdraw_credits(member, event["currency_penalty"])
                    event_text += f" (-{event['currency_penalty']} {currency_name})"
                
                event_messages.append(event_text)

            # Roll for success
            success = random.random() < success_chance
            
            if success:
                # Clear jail time
                await self.clear_jail_state(member)
                embed = discord.Embed(
                    title="🔓 Successful Jailbreak!",
                    description=scenario.format_text(scenario.success_text, user=member.mention),
                    color=discord.Color.green()
                )
            else:
                # Add 30% more time
                remaining_time = await self.get_jail_time_remaining(member)
                added_time = int(remaining_time * 0.3)
                new_until = int(time.time()) + remaining_time + added_time
                await self.update_jail_state(member, {"jail_until": new_until})
                
                # Create fail embed
                embed = discord.Embed(
                    title="⛓️ Failed Jailbreak!",
                    description=scenario.format_text(scenario.fail_text, user=member.mention),
                    color=discord.Color.red()
                )
                
                # Add penalty info
                minutes = remaining_time // 60
                seconds = remaining_time % 60
                new_minutes = int((remaining_time * 1.3) // 60)
                new_seconds = int((remaining_time * 1.3) % 60)
                embed.add_field(
                    name="⚖️ Penalty",
                    value=f"Your sentence has been increased by 30%!\n({minutes}m {seconds}s + 30% = ⏰ {new_minutes}m {new_seconds}s)",
                    inline=True
                )

            # Add chance field
            embed.add_field(
                name="🎲 Final Escape Chance",
                value=f"{success_chance:.1%}",
                inline=True
            )
            
            return success, embed, event_messages

        except Exception as e:
            raise JailbreakError(f"Failed to process jailbreak attempt: {str(e)}")

    async def format_jailbreak_embed(self, member: discord.Member, scenario: JailbreakScenario) -> discord.Embed:
        """Format the initial jailbreak attempt embed."""
        try:
            embed = discord.Embed(
                title="🔓 Jailbreak Attempt",
                description=scenario.format_text(scenario.attempt_text, user=member.mention),
                color=discord.Color.gold()
            )
            embed.add_field(
                name="📊 Base Success Chance",
                value=f"{scenario.base_chance:.1%}",
                inline=True
            )
            return embed
        except Exception as e:
            raise JailbreakError(f"Failed to format jailbreak embed: {str(e)}")

    async def format_jail_status(self, member: discord.Member) -> discord.Embed:
        """Format jail status into an embed."""
        try:
            state = await self.get_jail_state(member)
            remaining_time = await self.get_jail_time_remaining(member)
            
            if remaining_time <= 0:
                return discord.Embed(
                    title="🆓 Not in Jail",
                    description=f"{member.mention} is not currently in jail.",
                    color=discord.Color.green()
                )
            
            embed = discord.Embed(
                title="⛓️ Jail Status",
                description=f"{member.mention} is currently in jail!",
                color=discord.Color.red()
            )
            
            # Add time info
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            embed.add_field(
                name="⏰ Time Remaining",
                value=f"{minutes}m {seconds}s" + (" (Reduced by 20%)" if state["reduced_sentence"] else ""),
                inline=True
            )
            
            # Add notification status if they have the perk
            if await self.perk_manager.has_perk(member, "jail_notifier"):
                embed.add_field(
                    name="🔔 Notifications",
                    value="Enabled" if state["notify_on_release"] else "Disabled",
                    inline=True
                )
            
            # Add jailbreak attempt status
            embed.add_field(
                name="🔓 Jailbreak Attempt",
                value="Already Attempted" if state["attempted_jailbreak"] else "Not Attempted",
                inline=True
            )
            
            return embed
            
        except Exception as e:
            raise JailStateError(f"Failed to format jail status: {str(e)}")
