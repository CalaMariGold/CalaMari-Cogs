"""LootDrop cog for Red-DiscordBot - Drop random loot in channels for users to grab"""
from typing import Optional, Dict, List, Union, Tuple, Any, cast
import discord
from redbot.core import commands, Config, bank
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, humanize_list
import datetime
import random
from discord.ext import tasks
from collections import defaultdict
import asyncio
from .scenarios import SCENARIOS, Scenario
import time

# Default guild settings
DEFAULT_GUILD_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "channels": [],
    "min_credits": 100,
    "max_credits": 1000,
    "bad_outcome_chance": 30,
    "drop_timeout": 60,
    "min_frequency": 300,
    "max_frequency": 1800,
    "activity_timeout": 300,
    "last_drop": 0,
    "next_drop": 0,
    "messages": {"expired": "The opportunity has passed..."},
    "user_stats": {},  # {user_id: {"good": count, "bad": count}}
    "streak_bonus": 10,  # Percentage bonus per streak level
    "streak_max": 5,     # Maximum streak multiplier
    "streak_timeout": 24,  # Hours before streak resets
    "party_drop_chance": 5,  # Percentage chance for party drop
    "party_drop_min": 50,   # Min credits per person
    "party_drop_max": 200,  # Max credits per person
    "party_drop_timeout": 30  # Seconds to claim party drop
}


class ActiveDrop:
    """Represents an active loot drop in a channel
    
    Attributes
    ----------
    message: discord.Message
        The message containing the loot drop
    view: discord.ui.View
        The view containing the claim button
    created: int
        Unix timestamp of when the drop was created
    """
    def __init__(self, message: discord.Message, view: discord.ui.View, created: int) -> None:
        self.message: discord.Message = message
        self.view: discord.ui.View = view
        self.created: int = created


class LootDrop(commands.Cog):
    """Drop random loot in channels for users to grab
    
    This cog creates random loot drops in active channels that users can claim.
    It supports both regular drops (single claim) and party drops (multi-claim).
    
    Attributes
    ----------
    bot: Red
        The Red instance
    config: Config
        The config manager for guild settings
    active_drops: Dict[int, ActiveDrop]
        Currently active drops, keyed by guild ID
    tasks: Dict[int, asyncio.Task]
        Active timeout tasks, keyed by guild ID
    channel_last_message: Dict[int, int]
        Last message timestamp per channel
    channel_perms_cache: Dict[int, Tuple[int, bool]]
        Cache of channel permission checks
    """
    
    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        self.config: Config = Config.get_conf(
            self,
            identifier=582650109,
            force_registration=True
        )
        
        self.config.register_guild(**DEFAULT_GUILD_SETTINGS)
        
        self.active_drops: Dict[int, ActiveDrop] = {}
        self.tasks: Dict[int, asyncio.Task] = {}
        self.channel_last_message: Dict[int, int] = defaultdict(lambda: 0)
        self.channel_perms_cache: Dict[int, Tuple[int, bool]] = {}
        
        self.start_drops.start()
    
    def cog_unload(self) -> None:
        """Cleanup when cog is unloaded
        
        Cancels all tasks and removes active drops
        """
        # Stop the background task first
        self.start_drops.cancel()
        
        try:
            # Cancel all timeout tasks
            for task in self.tasks.values():
                task.cancel()
            
            # Clean up active drops
            for drop in self.active_drops.values():
                try:
                    self.bot.loop.create_task(drop.message.delete())
                except:
                    pass
        finally:
            # Clear all state
            self.active_drops.clear()
            self.tasks.clear()
            self.channel_last_message.clear()
            self.channel_perms_cache.clear()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Track channel activity"""
        if message.guild and not message.author.bot:
            # Update activity for both channels and threads
            self.channel_last_message[message.channel.id] = int(datetime.datetime.now().timestamp())
    
    async def channel_is_active(self, channel: Union[discord.TextChannel, discord.Thread]) -> bool:
        """Check if a channel has had message activity within the activity timeout"""
        now: int = int(datetime.datetime.now().timestamp())
        last_message: int = self.channel_last_message[channel.id]
        timeout: int = await self.config.guild(channel.guild).activity_timeout()
        
        # For threads, also check if they're still active
        if isinstance(channel, discord.Thread) and not channel.parent:
            return False
            
        return (now - last_message) < timeout
    
    async def has_channel_permissions(self, channel: Union[discord.TextChannel, discord.Thread]) -> bool:
        """Check if bot has required permissions in channel, with caching"""
        now: int = int(datetime.datetime.now().timestamp())
        cache_entry: Optional[Tuple[int, bool]] = self.channel_perms_cache.get(channel.id)
        
        if cache_entry and (now - cache_entry[0]) < 300:
            return cache_entry[1]
        
        # For threads, check parent channel permissions too
        if isinstance(channel, discord.Thread):
            if not channel.parent:
                return False
            parent_perms = channel.parent.permissions_for(channel.guild.me)
            if not parent_perms.send_messages:
                return False
                
        has_perms: bool = channel.permissions_for(channel.guild.me).send_messages
        self.channel_perms_cache[channel.id] = (now, has_perms)
        return has_perms
    
    async def get_active_channel(self, guild: discord.Guild) -> Optional[Union[discord.TextChannel, discord.Thread]]:
        """Get a random active channel from the configured channels"""
        channels: List[int] = await self.config.guild(guild).channels()
        active_channels: List[Union[discord.TextChannel, discord.Thread]] = []
        
        for channel_id in channels:
            channel = None
            # Try to get as text channel first
            channel = guild.get_channel(channel_id)
            # If not found, try to get as thread
            if not channel:
                for thread in guild.threads:
                    if thread.id == channel_id:
                        channel = thread
                        break
                        
            if channel and await self.channel_is_active(channel) and await self.has_channel_permissions(channel):
                active_channels.append(channel)
        
        return random.choice(active_channels) if active_channels else None
    
    @tasks.loop(seconds=30)
    async def start_drops(self) -> None:
        """Check for and create drops in all guilds"""
        for guild in self.bot.guilds:
            try:
                if not await self.config.guild(guild).enabled() or guild.id in self.active_drops:
                    continue
                
                now: int = int(datetime.datetime.now().timestamp())
                if now >= await self.config.guild(guild).next_drop():
                    if channel := await self.get_active_channel(guild):
                        await self.create_drop(channel)
                    await self.schedule_next_drop(guild)
            except Exception as e:
                if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                    await guild.system_channel.send(f"Error creating loot drop: {e}")
    
    @start_drops.before_loop
    async def before_start_drops(self) -> None:
        """Wait for bot to be ready before starting drops"""
        await self.bot.wait_until_ready()
    
    async def schedule_next_drop(self, guild: discord.Guild) -> None:
        """Schedule the next drop for a guild"""
        if not await self.config.guild(guild).enabled():
            return
            
        min_freq: int = await self.config.guild(guild).min_frequency()
        max_freq: int = await self.config.guild(guild).max_frequency()
        now: int = int(datetime.datetime.now().timestamp())
        
        await self.config.guild(guild).next_drop.set(now + random.randint(min_freq, max_freq))
    
    async def create_drop(self, channel: Union[discord.TextChannel, discord.Thread]) -> None:
        """Create a new loot drop in the specified channel"""
        if not channel.permissions_for(channel.guild.me).send_messages:
            return
            
        if channel.guild.id in self.active_drops:
            return
            
        # Check for party drop
        is_party = random.randint(1, 100) <= await self.config.guild(channel.guild).party_drop_chance()
        
        if is_party:
            await self.create_party_drop(channel)
        else:
            scenario = random.choice(SCENARIOS)
            timeout = await self.config.guild(channel.guild).drop_timeout()
            view = LootDropView(self, scenario, float(timeout))
            view.message = await channel.send(scenario["start"], view=view)
            
            self.active_drops[channel.guild.id] = ActiveDrop(
                message=view.message,
                view=view,
                created=int(datetime.datetime.now().timestamp())
            )
            
            # Start timeout task
            self.tasks[channel.guild.id] = asyncio.create_task(self._handle_drop_timeout(channel.guild.id, timeout))
    
    async def _handle_drop_timeout(self, guild_id: int, timeout: int) -> None:
        """Handle drop timeout and cleanup"""
        try:
            if guild_id in self.active_drops:
                drop = self.active_drops[guild_id]
                # Calculate remaining time based on when the drop was created
                now = int(datetime.datetime.now().timestamp())
                elapsed = now - drop.created
                remaining = max(0, timeout - elapsed)
                
                await asyncio.sleep(remaining)
                if guild_id in self.active_drops:
                    drop = self.active_drops[guild_id]
                    if not drop.view.claimed:
                        await drop.message.edit(content="The opportunity has passed...", view=None)
                    del self.active_drops[guild_id]
        except Exception:
            pass
        finally:
            if guild_id in self.tasks:
                del self.tasks[guild_id]
    
    async def create_party_drop(self, channel: Union[discord.TextChannel, discord.Thread]) -> None:
        """Create a party drop that everyone can claim
        
        Parameters
        ----------
        channel: Union[discord.TextChannel, discord.Thread]
            The channel to create the drop in
        """
        if channel.guild.id in self.active_drops:
            return
            
        timeout = await self.config.guild(channel.guild).party_drop_timeout()
        view = PartyDropView(self, timeout)
        message = await channel.send(
            "🎉 **PARTY DROP!** 🎉\n"
            "Everyone who clicks the button in the next "
            f"{timeout} seconds gets a prize!\n",
            view=view
        )
        view.message = message
        
        self.active_drops[channel.guild.id] = ActiveDrop(
            message=message,
            view=view,
            created=int(datetime.datetime.now().timestamp())
        )
        
        # Start timeout task
        self.tasks[channel.guild.id] = asyncio.create_task(self._handle_party_timeout(channel.guild.id, timeout))
    
    async def _handle_party_timeout(self, guild_id: int, timeout: int) -> None:
        """Handle party drop timeout and rewards
        
        Parameters
        ----------
        guild_id: int
            The guild ID for this party drop
        timeout: int
            Seconds to wait before processing rewards
        
        Notes
        -----
        Rewards are scaled based on reaction time:
        - Clicking within first 20% of timeout: 80-100% of max credits
        - Clicking within 20-40% of timeout: 60-80% of max credits
        - Clicking within 40-60% of timeout: 40-60% of max credits
        - Clicking within 60-80% of timeout: 20-40% of max credits
        - Clicking within 80-100% of timeout: min credits
        """
        try:
            await asyncio.sleep(timeout)
            
            if guild_id in self.active_drops:
                drop = self.active_drops[guild_id]
                view = cast(PartyDropView, drop.view)
                
                if not view.claimed_users:
                    await drop.message.edit(content="No one joined the party... 😢", view=None)
                else:
                    min_credits = await self.config.guild(drop.message.guild).party_drop_min()
                    max_credits = await self.config.guild(drop.message.guild).party_drop_max()
                    credit_range = max_credits - min_credits
                    
                    # Sort users by click speed
                    sorted_users = sorted(view.claimed_users.items(), key=lambda x: x[1])
                    
                    results = []
                    for position, (user_id, claim_time) in enumerate(sorted_users, 1):
                        user = drop.message.guild.get_member(int(user_id))
                        if user:
                            # Calculate reaction time and percentage of timeout
                            reaction_time = claim_time - view.start_time
                            time_percentage = (reaction_time / timeout) * 100
                            
                            # Calculate credits based on reaction time
                            if time_percentage <= 20:  # Super fast (80-100% of max)
                                credits = max_credits - int((time_percentage / 20) * (credit_range * 0.2))
                            elif time_percentage <= 40:  # Fast (60-80% of max)
                                credits = int(max_credits * 0.8) - int(((time_percentage - 20) / 20) * (credit_range * 0.2))
                            elif time_percentage <= 60:  # Medium (40-60% of max)
                                credits = int(max_credits * 0.6) - int(((time_percentage - 40) / 20) * (credit_range * 0.2))
                            elif time_percentage <= 80:  # Slow (20-40% of max)
                                credits = int(max_credits * 0.4) - int(((time_percentage - 60) / 20) * (credit_range * 0.2))
                            else:  # Very slow (min credits)
                                credits = min_credits
                            
                            await bank.deposit_credits(user, credits)
                            
                            # Update stats and streak
                            async with self.config.guild(drop.message.guild).user_stats() as stats:
                                if user_id not in stats:
                                    stats[user_id] = {"good": 0, "bad": 0, "streak": 0, "highest_streak": 0, "last_claim": 0}
                                
                                stats[user_id]["good"] += 1
                                
                                # Update streak if within timeout
                                now = int(datetime.datetime.now().timestamp())
                                streak_timeout = await self.config.guild(drop.message.guild).streak_timeout()
                                if now - stats[user_id]["last_claim"] < streak_timeout * 3600:
                                    stats[user_id]["streak"] += 1
                                    stats[user_id]["highest_streak"] = max(stats[user_id]["streak"], stats[user_id]["highest_streak"])
                                else:
                                    stats[user_id]["streak"] = 1
                                
                                stats[user_id]["last_claim"] = now
                                
                                # Add result with streak and timing info
                                streak_display = f" (🔥{stats[user_id]['streak']})" if stats[user_id]['streak'] > 1 else ""
                                position_emoji = ["🥇", "🥈", "🥉"][position-1] if position <= 3 else f"{position}th"
                                
                                # Add speed indicator based on time percentage
                                if time_percentage <= 20:
                                    speed = "💨 Super Fast!"
                                elif time_percentage <= 40:
                                    speed = "⚡ Fast!"
                                elif time_percentage <= 60:
                                    speed = "👍 Good"
                                elif time_percentage <= 80:
                                    speed = "🐌 Slow"
                                else:
                                    speed = "🦥 Very Slow"
                                
                                currency_name = await bank.get_currency_name(drop.message.guild)
                                results.append(
                                    f"{position_emoji} {user.mention}{streak_display}: {credits:,} {currency_name}\n"
                                    f"└ {speed} ({reaction_time:.2f}s)"
                                )
                    
                    await drop.message.edit(
                        content=f"🎊 **Party Drop Results!** 🎊\n"
                        f"{len(results)} party-goers claimed rewards:\n\n" +
                        "\n".join(results),
                        view=None
                    )
                
                del self.active_drops[guild_id]
                
        except Exception as e:
            if guild_id in self.active_drops:
                try:
                    await self.active_drops[guild_id].message.edit(content=f"Error processing party drop: {e}", view=None)
                except:
                    pass
                del self.active_drops[guild_id]
        finally:
            if guild_id in self.tasks:
                del self.tasks[guild_id]

    async def process_loot_claim(self, interaction: discord.Interaction) -> None:
        """Process a user's loot claim"""
        try:
            guild: discord.Guild = interaction.guild
            user: discord.Member = interaction.user
            
            min_credits: int = await self.config.guild(guild).min_credits()
            max_credits: int = await self.config.guild(guild).max_credits()
            bad_chance: int = await self.config.guild(guild).bad_outcome_chance()
            streak_bonus: int = await self.config.guild(guild).streak_bonus()
            streak_max: int = await self.config.guild(guild).streak_max()
            streak_timeout: int = await self.config.guild(guild).streak_timeout()
            currency_name: str = await bank.get_currency_name(guild)
            
            scenario: Scenario = next(
                (s for s in SCENARIOS if s["start"] == interaction.message.content),
                SCENARIOS[0]
            )
            
            amount: int = random.randint(min_credits, max_credits)
            is_bad: bool = random.randint(1, 100) <= bad_chance
            
            # Update user stats and streaks
            async with self.config.guild(guild).user_stats() as stats:
                now = int(datetime.datetime.now().timestamp())
                user_stats = stats.setdefault(str(user.id), {
                    "good": 0,
                    "bad": 0,
                    "streak": 0,
                    "last_claim": 0,
                    "highest_streak": 0
                })
                
                # Check if streak should reset due to timeout
                hours_since_last = (now - user_stats.get("last_claim", 0)) / 3600
                if hours_since_last > streak_timeout:
                    user_stats["streak"] = 0
                
                user_stats["last_claim"] = now
                
                try:
                    if is_bad:
                        amount = min(amount, await bank.get_balance(user))
                        await bank.withdraw_credits(user, amount)
                        message: str = scenario["bad"].format(user=user.mention, amount=f"{amount:,}", currency=currency_name)
                        user_stats["bad"] += 1
                        user_stats["streak"] = 0
                    else:
                        # Calculate streak bonus
                        streak = min(user_stats["streak"], streak_max)
                        bonus = int(amount * (streak * streak_bonus / 100))
                        total = amount + bonus
                        
                        await bank.deposit_credits(user, total)
                        if bonus > 0:
                            message: str = (
                                f"{scenario['good'].format(user=user.mention, amount=f'{total:,}', currency=currency_name)}\n"
                                f"(Base: {amount:,} + Streak Bonus: {bonus:,} [{streak}x])"
                            )
                        else:
                            message: str = scenario["good"].format(user=user.mention, amount=f"{total:,}", currency=currency_name)
                        
                        user_stats["good"] += 1
                        user_stats["streak"] += 1
                        user_stats["highest_streak"] = max(user_stats["streak"], user_stats.get("highest_streak", 0))
                    
                    # Add stats to message
                    message += f"\n-# (✅ {user_stats['good']} | ❌ {user_stats.get('bad', 0)} drops claimed | "
                    if user_stats["streak"] > 0:
                        message += f"🔥 {user_stats['streak']} streak"
                    else:
                        message += "❄️ streak lost"
                    position, _ = await self.get_leaderboard_position(guild, str(user.id))
                    message += f" | Rank #{position})"
                    
                    # Use followup instead of response since we might have already responded
                    if interaction.response.is_done():
                        await interaction.followup.send(message)
                    else:
                        await interaction.response.send_message(message)
                        
                except Exception as e:
                    if interaction.response.is_done():
                        await interaction.followup.send(f"Error processing claim: {e}", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"Error processing claim: {e}", ephemeral=True)
                    
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"Error processing claim: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Error processing claim: {e}", ephemeral=True)
    
    @commands.group()
    @commands.guild_only()
    async def lootdrop(self, ctx: commands.Context) -> None:
        """Random loot drops that appear in active channels
        
        Drops can be claimed by clicking a button. Features include:
        - Regular drops (single claim)
        - Party drops (everyone can claim)
        - Streak bonuses for consecutive claims
        - Risk/reward mechanics with good/bad outcomes
        - Leaderboards and statistics
        
        Use `[p]lootdrop set` to configure settings
        Use `[p]lootdrop stats` to view your stats
        Use `[p]lootdrop leaderboard` to view top claimers
        """
        pass
    
    @lootdrop.group(name="set")
    @commands.admin_or_permissions(administrator=True)
    async def lootdrop_set(self, ctx: commands.Context) -> None:
        """Configure LootDrop settings
        
        All settings are per-server. Available settings:
        - Toggle drops on/off
        - Add/remove channels
        - Credit amounts
        - Drop frequency and timeouts
        - Streak bonuses and timeouts
        - Party drop settings
        
        Use `[p]help LootDrop set` to see all settings
        """
        pass
    
    @lootdrop_set.command(name="toggle")
    async def lootdrop_set_toggle(self, ctx: commands.Context, on_off: Optional[bool] = None) -> None:
        """Toggle LootDrop on/off"""
        curr_state: bool = await self.config.guild(ctx.guild).enabled()
        if on_off is None:
            on_off = not curr_state
            
        await self.config.guild(ctx.guild).enabled.set(on_off)
        if on_off:
            await self.schedule_next_drop(ctx.guild)
            await ctx.send("LootDrop is now enabled! Drops will begin shortly.")
        else:
            await ctx.send("LootDrop is now disabled.")
    
    @lootdrop_set.command(name="addchannel")
    async def lootdrop_set_addchannel(
        self, 
        ctx: commands.Context, 
        channel: Union[discord.TextChannel, discord.Thread]
    ) -> None:
        """Add a channel or thread to the loot drop pool"""
        if isinstance(channel, discord.Thread) and not channel.parent:
            await ctx.send("That thread no longer exists!")
            return
            
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send("I don't have permission to send messages there!")
            return
            
        async with self.config.guild(ctx.guild).channels() as channels:
            if channel.id in channels:
                await ctx.send(f"{channel.mention} is already in the loot drop pool!")
                return
                
            channels.append(channel.id)
            
        await ctx.send(f"Added {channel.mention} to the loot drop pool!")

    @lootdrop_set.command(name="removechannel")
    async def lootdrop_set_removechannel(
        self, 
        ctx: commands.Context, 
        channel: Union[discord.TextChannel, discord.Thread]
    ) -> None:
        """Remove a channel or thread from the loot drop pool"""
        async with self.config.guild(ctx.guild).channels() as channels:
            if channel.id not in channels:
                await ctx.send(f"{channel.mention} is not in the loot drop pool!")
                return
                
            channels.remove(channel.id)
            
        await ctx.send(f"Removed {channel.mention} from the loot drop pool!")

    @lootdrop_set.command(name="credits")
    async def lootdrop_set_credits(self, ctx: commands.Context, min_credits: int, max_credits: int) -> None:
        """Set the credit range for drops"""
        currency_name = await bank.get_currency_name(ctx.guild)
        
        if min_credits < 1:
            await ctx.send(f"Minimum {currency_name} must be at least 1!")
            return
            
        if max_credits < min_credits:
            await ctx.send(f"Maximum {currency_name} must be greater than minimum {currency_name}!")
            return
            
        await self.config.guild(ctx.guild).min_credits.set(min_credits)
        await self.config.guild(ctx.guild).max_credits.set(max_credits)
        await ctx.send(f"Drops will now give between {min_credits:,} and {max_credits:,} {currency_name}!")

    @lootdrop_set.command(name="badchance")
    async def lootdrop_set_badchance(self, ctx: commands.Context, chance: int) -> None:
        """Set the chance of bad outcomes (0-100)"""
        if not 0 <= chance <= 100:
            await ctx.send("Chance must be between 0 and 100!")
            return
            
        await self.config.guild(ctx.guild).bad_outcome_chance.set(chance)
        await ctx.send(f"Bad outcome chance set to {chance}%")
    
    @lootdrop_set.command(name="timeout")
    async def lootdrop_set_timeout(self, ctx: commands.Context, seconds: int) -> None:
        """Set how long users have to claim a drop
        
        Parameters
        ----------
        seconds: int
            Number of seconds before the drop expires
            Example: 3600 = 1 hour, 1800 = 30 minutes
        """
        if seconds < 10:
            await ctx.send("Timeout must be at least 10 seconds!")
            return
            
        await self.config.guild(ctx.guild).drop_timeout.set(seconds)
        
        # Convert to a more readable format for the response
        if seconds >= 3600:
            time_str = f"{seconds // 3600} hours"
            if seconds % 3600:
                time_str += f" and {(seconds % 3600) // 60} minutes"
        elif seconds >= 60:
            time_str = f"{seconds // 60} minutes"
            if seconds % 60:
                time_str += f" and {seconds % 60} seconds"
        else:
            time_str = f"{seconds} seconds"
            
        await ctx.send(f"Users will now have {time_str} to claim drops!")
    
    @lootdrop_set.command(name="frequency")
    async def lootdrop_set_frequency(self, ctx: commands.Context, min_minutes: int, max_minutes: int) -> None:
        """Set how frequently drops appear"""
        if min_minutes < 1:
            await ctx.send("Minimum frequency must be at least 1 minute!")
            return
            
        if max_minutes < min_minutes:
            await ctx.send("Maximum frequency must be greater than minimum frequency!")
            return
            
        await self.config.guild(ctx.guild).min_frequency.set(min_minutes * 60)
        await self.config.guild(ctx.guild).max_frequency.set(max_minutes * 60)
        await self.schedule_next_drop(ctx.guild)
        await ctx.send(f"Drops will occur randomly between {min_minutes} and {max_minutes} minutes apart.")
    
    @lootdrop_set.command(name="activitytimeout")
    async def lootdrop_set_activitytimeout(self, ctx: commands.Context, minutes: int) -> None:
        """Set how long a channel can be inactive before drops are skipped"""
        if minutes < 1:
            await ctx.send("Timeout must be at least 1 minute!")
            return
            
        await self.config.guild(ctx.guild).activity_timeout.set(minutes * 60)
        await ctx.send(f"Channels will now be considered inactive after {minutes} minutes without messages.")
    
    @lootdrop_set.command(name="streakbonus")
    async def lootdrop_set_streakbonus(self, ctx: commands.Context, percentage: int) -> None:
        """Set the credit bonus percentage per streak level
        
        Example: A bonus of 10 means each streak level adds 10% more credits
        So streak 3 would give a 30% bonus
        """
        if percentage < 0:
            await ctx.send("Bonus percentage must be positive!")
            return
            
        await self.config.guild(ctx.guild).streak_bonus.set(percentage)
        await ctx.send(f"Streak bonus set to {percentage}% per level")
    
    @lootdrop_set.command(name="streakmax")
    async def lootdrop_set_streakmax(self, ctx: commands.Context, max_level: int) -> None:
        """Set the maximum streak multiplier level
        
        Example: A max of 5 means streaks cap at 5x the bonus
        """
        if max_level < 1:
            await ctx.send("Maximum streak level must be at least 1!")
            return
            
        await self.config.guild(ctx.guild).streak_max.set(max_level)
        await ctx.send(f"Maximum streak level set to {max_level}")
    
    @lootdrop_set.command(name="streaktimeout")
    async def lootdrop_set_streaktimeout(self, ctx: commands.Context, hours: int) -> None:
        """Set how many hours before a streak resets
        
        Example: A timeout of 24 means you must claim within 24 hours to keep streak
        """
        if hours < 1:
            await ctx.send("Timeout must be at least 1 hour!")
            return
            
        await self.config.guild(ctx.guild).streak_timeout.set(hours)
        await ctx.send(f"Streak timeout set to {hours} hours")
    
    @lootdrop_set.command(name="partychance")
    async def lootdrop_set_partychance(self, ctx: commands.Context, chance: int) -> None:
        """Set the chance of a party drop appearing (0-100)
        
        Party drops allow everyone to claim within a time limit
        """
        if not 0 <= chance <= 100:
            await ctx.send("Chance must be between 0 and 100!")
            return
            
        await self.config.guild(ctx.guild).party_drop_chance.set(chance)
        await ctx.send(f"Party drop chance set to {chance}%")
    
    @lootdrop_set.command(name="partycredits")
    async def lootdrop_set_partycredits(self, ctx: commands.Context, min_credits: int, max_credits: int) -> None:
        """Set the credit range for party drops
        
        Each person who claims gets this amount
        """
        currency_name = await bank.get_currency_name(ctx.guild)
        
        if min_credits < 1:
            await ctx.send(f"Minimum {currency_name} must be at least 1!")
            return
            
        if max_credits < min_credits:
            await ctx.send(f"Maximum {currency_name} must be greater than minimum {currency_name}!")
            return
            
        await self.config.guild(ctx.guild).party_drop_min.set(min_credits)
        await self.config.guild(ctx.guild).party_drop_max.set(max_credits)
        await ctx.send(f"Party drops will now give between {min_credits:,} and {max_credits:,} {currency_name} per person!")

    @lootdrop_set.command(name="partytimeout")
    async def lootdrop_set_partytimeout(self, ctx: commands.Context, seconds: int) -> None:
        """Set how long users have to claim a party drop"""
        if seconds < 5:
            await ctx.send("Timeout must be at least 5 seconds!")
            return
            
        await self.config.guild(ctx.guild).party_drop_timeout.set(seconds)
        await ctx.send(f"Users will now have {seconds} seconds to claim party drops!")
    
    @commands.is_owner()
    @lootdrop.command(name="wipedata")
    async def lootdrop_wipedata(self, ctx: commands.Context) -> None:
        """⚠️ [Owner Only] Completely wipe all LootDrop data
        
        This will erase:
        - All guild settings
        - All user stats and streaks
        - All active drops
        
        This action cannot be undone!
        """
        # Ask for confirmation
        msg = await ctx.send(
            "⚠️ **WARNING**: This will completely wipe all LootDrop data across all servers!\n"
            "This includes all settings, stats, and streaks.\n\n"
            "**This action cannot be undone!**\n\n"
            "Type `yes, wipe all data` to confirm."
        )
        
        try:
            response = await self.bot.wait_for(
                "message",
                timeout=30.0,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
        except asyncio.TimeoutError:
            await msg.edit(content="Data wipe cancelled - timed out.")
            return
            
        if response.content.lower() != "yes, wipe all data":
            await msg.edit(content="Data wipe cancelled - incorrect confirmation.")
            return
            
        # Stop all active drops and tasks
        self.start_drops.cancel()
        for task in self.tasks.values():
            task.cancel()
        
        try:
            # Clean up active drops
            for drop in self.active_drops.values():
                try:
                    await drop.message.delete()
                except:
                    pass
                    
            # Clear all state
            self.active_drops.clear()
            self.tasks.clear()
            self.channel_last_message.clear()
            self.channel_perms_cache.clear()
            
            # Clear all data from config
            await self.config.clear_all()
            
            # Restart the drop task
            self.start_drops.start()
            
            await msg.edit(content="✅ All LootDrop data has been wiped!")
            
        except Exception as e:
            await msg.edit(content=f"Error wiping data: {e}")
    
    @commands.is_owner()
    @lootdrop.command(name="wipestats")
    async def lootdrop_wipestats(self, ctx: commands.Context) -> None:
        """⚠️ [Owner Only] Wipe all user stats and streaks
        
        This will erase:
        - All user stats (good/bad drops)
        - All user streaks
        - Leaderboard data
        
        This action cannot be undone!
        Settings and active drops will be preserved.
        """
        # Ask for confirmation
        msg = await ctx.send(
            "⚠️ **WARNING**: This will wipe all user stats and streaks across all servers!\n"
            "This includes all drop counts, streaks, and leaderboard data.\n\n"
            "**This action cannot be undone!**\n"
            "Server settings and active drops will be preserved.\n\n"
            "Type `yes, wipe stats` to confirm."
        )
        
        try:
            response = await self.bot.wait_for(
                "message",
                timeout=30.0,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
        except asyncio.TimeoutError:
            await msg.edit(content="Stats wipe cancelled - timed out.")
            return
            
        if response.content.lower() != "yes, wipe stats":
            await msg.edit(content="Stats wipe cancelled - incorrect confirmation.")
            return
            
        try:
            # Get all guild data
            all_guilds = await self.config.all_guilds()
            
            # Clear only user_stats for each guild
            for guild_id in all_guilds:
                async with self.config.guild_from_id(guild_id).user_stats() as stats:
                    stats.clear()
            
            await msg.edit(content="✅ All user stats and streaks have been wiped!")
            
        except Exception as e:
            await msg.edit(content=f"Error wiping stats: {e}")
    
    @lootdrop.command(name="force")
    @commands.admin_or_permissions(administrator=True)
    async def lootdrop_force(self, ctx: commands.Context, channel: Optional[Union[discord.TextChannel, discord.Thread]] = None) -> None:
        """Force a lootdrop to appear"""
        channel = channel or ctx.channel
        
        if channel.guild.id in self.active_drops:
            await ctx.send("There's already an active drop in this server! Wait for it to be claimed or expire.")
            return
            
        if not channel.permissions_for(channel.guild.me).send_messages:
            await ctx.send(f"I don't have permission to send messages in {channel.mention}!")
            return
        
        try:
            await self.create_drop(channel)
            await self.config.guild(channel.guild).last_drop.set(int(datetime.datetime.now().timestamp()))
        except Exception as e:
            await ctx.send(f"Error creating drop: {e}")
    
    @lootdrop.command(name="forceparty")
    @commands.admin_or_permissions(administrator=True)
    async def lootdrop_force_party(self, ctx: commands.Context, channel: Optional[Union[discord.TextChannel, discord.Thread]] = None) -> None:
        """Force a party drop to appear
        
        Everyone who clicks the button gets credits!
        """
        channel = channel or ctx.channel
        
        if channel.guild.id in self.active_drops:
            await ctx.send("There's already an active drop in this server! Wait for it to be claimed or expire.")
            return
            
        if not channel.permissions_for(channel.guild.me).send_messages:
            await ctx.send(f"I don't have permission to send messages in {channel.mention}!")
            return
        
        try:
            await self.create_party_drop(channel)
            await self.config.guild(channel.guild).last_drop.set(int(datetime.datetime.now().timestamp()))
        except Exception as e:
            await ctx.send(f"Error creating party drop: {e}")
    
    @lootdrop.command(name="stats")
    async def lootdrop_stats(self, ctx: commands.Context, user: Optional[discord.Member] = None) -> None:
        """View loot drop statistics for a user"""
        user = user or ctx.author
        stats = await self.config.guild(ctx.guild).user_stats()
        user_stats = stats.get(str(user.id), {
            "good": 0, 
            "bad": 0,
            "streak": 0,
            "highest_streak": 0
        })
        
        total = user_stats["good"] + user_stats.get("bad", 0)
        if total == 0:
            await ctx.send(f"{user.mention} hasn't claimed any drops yet!")
            return
            
        success_rate = (user_stats["good"] / total) * 100
        streak_bonus = await self.config.guild(ctx.guild).streak_bonus()
        current_bonus = min(user_stats["streak"], await self.config.guild(ctx.guild).streak_max()) * streak_bonus
        
        embed = discord.Embed(
            title="🎲 Drop Statistics",
            description=f"Stats for {user.mention}",
            color=discord.Color.blue()
        )
        
        stats_text = (
            f"**Total Drops:** {total:,}\n"
            f"**Successful:** ✅ {user_stats['good']:,}\n"
            f"**Bad Luck:** ❌ {user_stats.get('bad', 0):,}\n"
            f"**Success Rate:** {success_rate:.1f}%\n\n"
            f"**Current Streak:** 🔥 {user_stats['streak']}\n"
            f"**Highest Streak:** ⭐ {user_stats.get('highest_streak', 0)}\n"
            f"**Current Bonus:** +{current_bonus}% credits"
        )
        
        embed.add_field(name="📊 Statistics", value=stats_text, inline=False)
        await ctx.send(embed=embed)
    
    @lootdrop.command(name="leaderboard", aliases=["lb"])
    async def lootdrop_leaderboard(self, ctx: commands.Context) -> None:
        """View the loot drop leaderboard (Top 5)"""
        _, leaderboard = await self.get_leaderboard_position(ctx.guild, str(ctx.author.id))
        
        if not leaderboard:
            await ctx.send("No drops have been claimed yet!")
            return
        
        embed = discord.Embed(
            title="🏆 LootDrop Leaderboard",
            color=discord.Color.gold()
        )
        
        # Get top 5 users
        description = []
        for i, (user_id, total, good, highest_streak) in enumerate(leaderboard[:5], 1):
            user = ctx.guild.get_member(int(user_id))
            if not user:
                continue
                
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "👑")
            success_rate = (good / total) * 100 if total > 0 else 0
            
            description.append(
                f"{medal} **#{i}** {user.mention}\n"
                f"└ {total:,} drops (✅ {good:,} | {success_rate:.1f}% success) | ⭐ Highest Streak: {highest_streak}"
            )
        
        if description:
            embed.description = "\n\n".join(description)
        else:
            embed.description = "No valid leaderboard entries found"
        
        # Add author's position if not in top 5
        author_pos, _ = await self.get_leaderboard_position(ctx.guild, str(ctx.author.id))
        if author_pos > 5:
            stats = await self.config.guild(ctx.guild).user_stats()
            author_stats = stats.get(str(ctx.author.id), {"good": 0, "bad": 0, "highest_streak": 0})
            total = author_stats["good"] + author_stats.get("bad", 0)
            success_rate = (author_stats["good"] / total) * 100 if total > 0 else 0
            
            embed.add_field(
                name="Your Position",
                value=(
                    f"#{author_pos} with {total:,} drops "
                    f"(✅ {author_stats['good']:,} | {success_rate:.1f}% success) | "
                    f"⭐ Highest Streak: {author_stats.get('highest_streak', 0)}"
                ),
                inline=False
            )
        
        await ctx.send(embed=embed)

    @lootdrop.command(name="settings")
    async def lootdrop_settings(self, ctx: commands.Context) -> None:
        """View current LootDrop settings"""
        settings: Dict[str, Any] = await self.config.guild(ctx.guild).all()
        currency_name = await bank.get_currency_name(ctx.guild)
        
        channels: List[str] = []
        for channel_id in settings["channels"]:
            # Try to get as text channel first
            channel = ctx.guild.get_channel(channel_id)
            # If not found, try to get as thread
            if not channel:
                for thread in ctx.guild.threads:
                    if thread.id == channel_id:
                        channel = thread
                        break
            
            if channel:
                channels.append(channel.mention)
                
        embed: discord.Embed = discord.Embed(
            title="💰 LootDrop Settings",
            description=f"**Status:** {'🟢 Enabled' if settings['enabled'] else '🔴 Disabled'}",
            color=discord.Color.gold() if settings['enabled'] else discord.Color.greyple()
        )
        
        # Channel Settings
        if channels:
            embed.add_field(
                name="📝 Channels",
                value=humanize_list(channels),
                inline=False
            )
        else:
            embed.add_field(
                name="📝 Channels",
                value="*No channels configured*\nUse `lootdrop set addchannel` to add channels or threads",
                inline=False
            )
        
        # Drop Settings
        drop_settings = (
            f"**{currency_name}:** {settings['min_credits']:,} - {settings['max_credits']:,}\n"
            f"**Bad Outcome:** {settings['bad_outcome_chance']}% chance\n"
            f"**Claim Time:** {settings['drop_timeout']} seconds\n"
            f"**Frequency:** {settings['min_frequency'] // 60} - {settings['max_frequency'] // 60} minutes"
        )
        embed.add_field(name="⚙️ Drop Settings", value=drop_settings, inline=False)
        
        # Activity Settings
        activity_settings = (
            f"**Timeout:** {settings['activity_timeout'] // 60} minutes of inactivity\n"
            "*Channels must have recent messages to receive drops*"
        )
        embed.add_field(name="⏰ Activity Settings", value=activity_settings, inline=False)
        
        # Streak Settings
        streak_settings = (
            f"**Bonus:** {settings['streak_bonus']}% per level\n"
            f"**Max Streak:** {settings['streak_max']}x\n"
            f"**Timeout:** {settings['streak_timeout']} hours"
        )
        embed.add_field(name="🔥 Streak Settings", value=streak_settings, inline=False)
        
        # Party Drop Settings
        party_settings = (
            f"**Chance:** {settings['party_drop_chance']}% chance\n"
            f"**{currency_name}:** {settings['party_drop_min']:,} - {settings['party_drop_max']:,}\n"
            f"**Timeout:** {settings['party_drop_timeout']} seconds"
        )
        embed.add_field(name="🎉 Party Drop Settings", value=party_settings, inline=False)
        
        # Next Drop Info
        if settings["enabled"]:
            now: int = int(datetime.datetime.now().timestamp())
            next_drop: int = settings["next_drop"]
            
            if next_drop <= now:
                next_drop_text = "**🎉 Drop is due now!**"
            else:
                minutes_left: int = (next_drop - now) // 60
                seconds_left: int = (next_drop - now) % 60
                
                if minutes_left > 0:
                    next_drop_text = f"**Next drop in {minutes_left}m {seconds_left}s**"
                else:
                    next_drop_text = f"**Next drop in {seconds_left}s**"
            
            embed.add_field(name="⏳ Next Drop", value=next_drop_text, inline=False)
        
        # Footer with command hint
        embed.set_footer(text="Use 'help lootdrop' to see all commands")
                
        await ctx.send(embed=embed)

    async def get_leaderboard_position(self, guild: discord.Guild, user_id: str) -> Tuple[int, List[Tuple[str, int, int, int]]]:
        """Get user's position and full leaderboard data"""
        stats = await self.config.guild(guild).user_stats()
        
        # Convert stats to list of (user_id, total_claims, good_claims, highest_streak)
        leaderboard = [
            (uid, data["good"] + data.get("bad", 0), data["good"], data.get("highest_streak", 0))
            for uid, data in stats.items()
            if data["good"] + data.get("bad", 0) > 0  # Only include users with at least one drop
        ]
        
        # Sort by total claims (desc) and then highest streak (desc)
        leaderboard.sort(key=lambda x: (x[1], x[3]), reverse=True)
        
        # Find user's position (1-based index)
        # If user has drops but somehow not in leaderboard, give last place instead of 0
        user_stats = stats.get(user_id, {"good": 0, "bad": 0})
        total_drops = user_stats["good"] + user_stats.get("bad", 0)
        
        if total_drops == 0:
            position = 0
        else:
            position = next((i + 1 for i, (uid, _, _, _) in enumerate(leaderboard) if uid == user_id), len(leaderboard) + 1)
        
        return position, leaderboard


class DropButton(discord.ui.Button['LootDropView']):
    """Button for claiming regular loot drops
    
    This button is used for single-claim drops where only one user can claim the reward.
    The button is removed after a successful claim.
    
    Attributes
    ----------
    scenario: Scenario
        The scenario this button is for
    """
    def __init__(self, scenario: Scenario) -> None:
        super().__init__(
            style=discord.ButtonStyle.success,
            emoji=scenario["button_emoji"],
            label=scenario["button_text"]
        )
        self.scenario = scenario
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """Handle button press
        
        Parameters
        ----------
        interaction: discord.Interaction
            The interaction that triggered this callback
        """
        if interaction.user.bot:
            return
            
        assert self.view is not None
        
        if self.view.claimed:
            await interaction.response.send_message("This drop has already been claimed!", ephemeral=True)
            return
            
        self.view.claimed = True
        await interaction.response.defer()
        
        # Remove from active drops and cancel timeout task
        if interaction.guild_id in self.view.cog.active_drops:
            del self.view.cog.active_drops[interaction.guild_id]
            if interaction.guild_id in self.view.cog.tasks:
                self.view.cog.tasks[interaction.guild_id].cancel()
                del self.view.cog.tasks[interaction.guild_id]
            
        await self.view.cog.process_loot_claim(interaction)
        try:
            await interaction.message.edit(view=None)
        except:
            pass


class LootDropView(discord.ui.View):
    """View for regular loot drops
    
    This view contains a single button that can be claimed once.
    After claiming, the button is removed and rewards are distributed.
    
    Attributes
    ----------
    cog: LootDrop
        The cog instance that created this view
    message: Optional[discord.Message]
        The message containing this view
    claimed: bool
        Whether this drop has been claimed
    scenario: Scenario
        The scenario for this drop
    """
    def __init__(self, cog: 'LootDrop', scenario: Scenario, timeout: float) -> None:
        super().__init__(timeout=timeout)
        self.cog: 'LootDrop' = cog
        self.message: Optional[discord.Message] = None
        self.claimed: bool = False
        self.scenario: Scenario = scenario
        self.add_item(DropButton(scenario))
    
    async def on_timeout(self) -> None:
        """Handle view timeout
        
        Removes the button and updates the message when the drop expires
        """
        if self.message and not self.claimed:
            try:
                await self.message.edit(content="The opportunity has passed...", view=None)
            except:
                pass


class PartyDropView(discord.ui.View):
    """View for party drops that multiple users can claim
    
    This view allows multiple users to claim rewards within a time window.
    The button remains active until timeout, allowing multiple users to join.
    
    Attributes
    ----------
    cog: LootDrop
        The cog instance that created this view
    claimed_users: Dict[str, float]
        Dict of user IDs to their claim timestamps
    message: Optional[discord.Message]
        The message containing this view
    start_time: float
        When the party drop was created
    """
    def __init__(self, cog: 'LootDrop', timeout: float) -> None:
        super().__init__(timeout=timeout)
        self.cog: 'LootDrop' = cog
        self.claimed_users: Dict[str, float] = {}
        self.message: Optional[discord.Message] = None
        self.start_time: float = time.time()
    
    @discord.ui.button(label="Claim Party Drop!", emoji="🎊", style=discord.ButtonStyle.success)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Handle party drop claims
        
        Parameters
        ----------
        interaction: discord.Interaction
            The interaction that triggered this callback
        button: discord.ui.Button
            The button that was clicked
        """
        if interaction.user.bot:
            return
            
        if str(interaction.user.id) in self.claimed_users:
            await interaction.response.send_message("You've already claimed this party drop!", ephemeral=True)
            return
            
        # Add user to claimed list with timestamp
        self.claimed_users[str(interaction.user.id)] = time.time()
        
        # Update button label to show number of participants
        button.label = f"Join Party! ({len(self.claimed_users)} joined)"
        
        # Acknowledge the interaction and update button
        await interaction.response.edit_message(view=self)
        
        # Send confirmation
        await interaction.followup.send("🎉 You've joined the party! Wait for rewards...", ephemeral=True)
    
    async def on_timeout(self) -> None:
        """Handle view timeout
        
        Called when the party drop timer expires. The button will be removed
        and rewards will be processed by the cog's timeout handler.
        """
        if self.message:
            try:
                await self.message.edit(view=None)
            except:
                pass
