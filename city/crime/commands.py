"""Commands for the crime system."""

from redbot.core import commands, bank
from redbot.core.utils.chat_formatting import box, humanize_number
from redbot.core.i18n import Translator
import discord
import random
import time
import asyncio
from .scenarios import get_random_scenario, get_random_jailbreak_scenario
from .views import CrimeListView, BailView, CrimeView, TargetSelectionView, CrimeButton
from .data import CRIME_TYPES, DEFAULT_GUILD, DEFAULT_MEMBER
from datetime import datetime
from ..utils import (
    format_cooldown_time, 
    get_crime_emoji, 
    format_crime_description
)

_ = Translator("Crime", __file__)

class CrimeCommands:
    """Crime commands mixin."""

    @commands.group(name="crime", invoke_without_command=True)
    async def crime(self, ctx: commands.Context):
        """Commit crimes to earn credits.

        This command group provides access to the crime system.
        
        Commands:
        - No subcommand: Shows available crimes
        - commit: Choose a crime to commit
        - status: View your crime statistics
        - leaderboard: View the crime leaderboard
        - bail: Attempt to pay bail and get out of jail
        - jailbreak: Attempt to break out of jail
        
        Admin Commands:
        - set: Configure crime system settings
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @crime.command(name="commit")
    async def crime_commit(self, ctx: commands.Context):
        """Choose a crime to commit
        
        Available crimes:
        - Pickpocket: Low risk, target users for small rewards
        - Mugging: Medium risk, target users for medium rewards
        - Store Robbery: Medium risk, no target needed
        - Bank Heist: High risk, high rewards
        
        Getting caught will send you to jail!
        """
        try:
            # Get guild settings
            settings = await self.config.guild(ctx.guild).global_settings()
            crime_options = await self.config.guild(ctx.guild).crime_options()
            
            # Check jail status
            jail_remaining = await self.get_jail_time_remaining(ctx.author)
            jail_status = ""
            if jail_remaining > 0:
                if jail_remaining > 3600:  # More than 1 hour
                    hours = jail_remaining // 3600
                    minutes = (jail_remaining % 3600) // 60
                    jail_status = f"⛓️ **JAILED** for {hours}h {minutes}m"
                else:
                    minutes = jail_remaining // 60
                    seconds = jail_remaining % 60
                    jail_status = f"⛓️ **JAILED** for {minutes}m {seconds}s"
            
            # Create embed with crime options
            embed = discord.Embed(
                title="🦹‍♂️ Criminal Activities",
                description=_(
                    "Choose your next heist wisely...\n"
                    "{jail_status}\n"
                    "**Fines:**\n"
                    "🟢 Low Risk: 30-35% of max reward\n"
                    "🟡 Medium Risk: 40-45% of max reward\n"
                    "🔴 High Risk: 45-50% of max reward\n\n"
                ).format(
                    jail_status=jail_status + "\n" if jail_status else ""
                ),
                color=await ctx.embed_color()
            )
            
            # Add crime options to embed
            crimes = list(crime_options.items())
            for i in range(0, len(crimes), 2):
                # Get current crime
                crime_type, data = crimes[i]
                
                # Get cooldown status
                remaining = await self.get_remaining_cooldown(ctx.author, crime_type)
                status = format_cooldown_time(remaining)
                
                # Format description
                description = format_crime_description(crime_type, data, status)
                
                # Check if there's a next crime to pair with
                if i + 1 < len(crimes):
                    # Get next crime
                    next_crime_type, next_data = crimes[i + 1]
                    
                    # Get cooldown status for next crime
                    next_remaining = await self.get_remaining_cooldown(ctx.author, next_crime_type)
                    next_status = format_cooldown_time(next_remaining)
                    
                    # Format next description
                    next_description = format_crime_description(next_crime_type, next_data, next_status)
                    
                    # Add both crimes side by side
                    embed.add_field(
                        name=f"{get_crime_emoji(crime_type)} {crime_type.replace('_', ' ').title()}",
                        value=description,
                        inline=True
                    )
                    embed.add_field(
                        name=f"{get_crime_emoji(next_crime_type)} {next_crime_type.replace('_', ' ').title()}",
                        value=next_description,
                        inline=True
                    )
                    # Add empty field to force next pair to start on new line
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
                else:
                    # Add single crime if no pair
                    embed.add_field(
                        name=f"{get_crime_emoji(crime_type)} {crime_type.replace('_', ' ').title()}",
                        value=description,
                        inline=True
                    )
            
            embed.set_footer(text="Use the buttons below to choose a crime")
            
            # Create view with crime buttons
            view = CrimeListView(self, ctx, crime_options)
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
            # Update button states based on jail and cooldowns
            await view.update_button_states()
            
        except Exception as e:
            await ctx.send(_("An error occurred while setting up the crime options. Please try again. Error: {}").format(str(e)))

    @crime.command(name="status")
    async def crime_status(self, ctx: commands.Context, user: discord.Member = None):
        """View your current crime status
        
        Parameters
        ----------
        user : discord.Member, optional
            The user to check status for. If not provided, shows your own status."""
        try:
            # Get member data
            target = user or ctx.author
            member_data = await self.config.member(target).all()
            settings = await self.config.guild(ctx.guild).global_settings()
            crime_options = await self.config.guild(ctx.guild).crime_options()

            # Create status embed
            embed = discord.Embed(
                title="🦹‍♂️ Criminal Profile",
                description=f"Status report for {target.mention}",
                color=await ctx.embed_color()
            )
            
            # Set thumbnail to user's avatar
            embed.set_thumbnail(url=target.display_avatar.url)
            
            # Check jail status
            remaining_jail = await self.get_jail_time_remaining(target)
            if remaining_jail > 0:
                embed.add_field(
                    name="⚖️ __Jail Status__",
                    value=f"🔒 In jail for {format_cooldown_time(remaining_jail)}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚖️ __Jail Status__",
                    value="🆓 Not in jail",
                    inline=False
                )

            # Add crime statistics in two columns
            stats_left = [
                f"**{await bank.get_currency_name(ctx.guild)} Earned:** {humanize_number(member_data['total_credits_earned'])}",
                f"**Crimes:** ✅ {member_data['total_successful_crimes']} | ❌ {member_data['total_failed_crimes']}",
                f"**{await bank.get_currency_name(ctx.guild)} Stolen:** {humanize_number(member_data['total_stolen_from'])}",
                f"**Largest Heist:** {humanize_number(member_data['largest_heist'])}"
            ]
            
            # Calculate success rate
            total_crimes = member_data['total_successful_crimes'] + member_data['total_failed_crimes']
            success_rate = (member_data['total_successful_crimes'] / total_crimes * 100) if total_crimes > 0 else 0
            
            stats_right = [
                f"**Total Fines:** {humanize_number(member_data['total_fines_paid'])}",
                f"**Total Bail:** {humanize_number(member_data['total_bail_paid'])}",
                f"**{await bank.get_currency_name(ctx.guild)} Lost:** {humanize_number(member_data['total_stolen_by'])}",
                f"**Success Rate:** {success_rate:.1f}%" if total_crimes > 0 else "**Success Rate:** N/A"
            ]
            
            embed.add_field(
                name="📊 __Crime Statistics__",
                value="\n".join(stats_left),
                inline=True
            )
            
            embed.add_field(
                name="💰 __Financial Impact__",
                value="\n".join(stats_right),
                inline=True
            )
            
            # Add empty field to force next section to new line
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Add crime cooldowns in a more compact format
            cooldowns = []
            for crime_type, data in crime_options.items():
                if not data.get("enabled", True):
                    continue
                    
                remaining = await self.get_remaining_cooldown(target, crime_type)
                crime_name = crime_type.replace('_', ' ').title()
                cooldowns.append(
                    f"{get_crime_emoji(crime_type)} **{crime_name}:** {format_cooldown_time(remaining)}"
                )
            
            if cooldowns:
                # Split cooldowns into two columns
                mid = len(cooldowns) // 2 + len(cooldowns) % 2
                
                embed.add_field(
                    name="📅 __Crime Cooldowns__",
                    value="\n".join(cooldowns[:mid]),
                    inline=True
                )
                
                if len(cooldowns) > mid:
                    embed.add_field(
                        name="\u200b",
                        value="\n".join(cooldowns[mid:]),
                        inline=True
                    )
                    
                    # Add empty field to maintain grid layout
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Add last target if any
            if member_data['last_target']:
                try:
                    last_target = await ctx.guild.fetch_member(member_data['last_target'])
                    if last_target:
                        embed.add_field(
                            name="🎯 __Last Target__",
                            value=last_target.mention,
                            inline=True
                        )
                except discord.NotFound:
                    pass
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            await ctx.send(_("An error occurred while retrieving your crime status. Please try again. Error: {}").format(str(e)))

    @crime.command(name="bail")
    async def crime_bail(self, ctx: commands.Context):
        """Pay bail to get out of jail early
        
        Bail cost increases with remaining jail time.
        Cost is calculated as: remaining_minutes * base_bail_rate
        """
        try:
            # Check if user is in jail
            jail_time = await self.get_jail_time_remaining(ctx.author)
            if jail_time <= 0:
                await ctx.send(_("You're not in jail!"))
                return
                
            # Get settings
            settings = await self.config.guild(ctx.guild).global_settings()
            if not settings.get("allow_bail", True):
                await ctx.send(_("Bail is not allowed in this server!"))
                return
                
            # Calculate bail cost based on remaining time
            bail_cost = int(settings.get("bail_cost_multiplier", 1.5) * jail_time)
            
            # Check if user can afford bail
            if not await bank.can_spend(ctx.author, bail_cost):
                await ctx.send(
                    _("💵❌You don't have enough {currency} to pay the bail amount of {amount}!").format(
                        currency=await bank.get_currency_name(ctx.guild),
                        amount=bail_cost
                    )
                )
                return
                
            # Create bail view
            view = BailView(self, ctx, bail_cost, jail_time)
            
            # Get current balance
            current_balance = await bank.get_balance(ctx.author)
            currency_name = await bank.get_currency_name(ctx.guild)
            
            # Create embed for bail prompt
            embed = discord.Embed(
                title="💰 Bail Payment Available",
                description=(
                    "You can pay bail to get out of jail immediately, or wait out your sentence.\n\n"
                    f"**Time Remaining:** {format_cooldown_time(jail_time, include_emoji=False)}\n"
                    f"**Bail Cost:** {bail_cost:,} {currency_name}\n"
                    f"**Current Balance:** {current_balance:,} {currency_name}\n\n"
                ),
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            
            # Send bail prompt
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            
            # Reset attempted jailbreak flag when bailing out
            async with self.config.member(ctx.author).all() as member_data:
                member_data["attempted_jailbreak"] = False
                
        except Exception as e:
            await ctx.send(_("An error occurred while processing your bail request. Please try again. Error: {}").format(str(e)))

    @crime.command(name="jailbreak")
    async def crime_jailbreak(self, ctx: commands.Context):
        """Attempt to break out of jail
        
        Success chance is based on remaining jail time:
        - 1-5 minutes: 60% chance
        - 6-15 minutes: 40% chance
        - 16+ minutes: 20% chance
        
        Failed attempts add more jail time!
        """
        try:
            # Check if user is in jail
            jail_time = await self.get_jail_time_remaining(ctx.author)
            if jail_time <= 0:
                await ctx.send(_("You're not in jail!"))
                return
                
            # Get member data
            member_data = await self.config.member(ctx.author).all()
            
            # Check if already attempted jailbreak this sentence
            if member_data.get("attempted_jailbreak", False):
                await ctx.send(_("You've already attempted to break out this sentence!"))
                return

            # Mark jailbreak as attempted
            async with self.config.member(ctx.author).all() as member_data:
                member_data["attempted_jailbreak"] = True

            # Get random scenario
            scenario = get_random_jailbreak_scenario()
            success_chance = scenario["base_chance"]

            # Send attempt message
            attempt_msg = await ctx.send(_(scenario['attempt_text']).format(
                user=ctx.author.mention
            ))

            # Add suspense delay
            await asyncio.sleep(3)

            # Random event (now 100% chance)
            event = random.choice(scenario['events'])
            event_text = event['text']
            # Format event text with currency name
            currency_name = await bank.get_currency_name(ctx.guild)
            event_text = event_text.format(currency=currency_name)
            
            # Apply chance modifiers and log them
            original_chance = success_chance
            if "chance_bonus" in event:
                success_chance = min(1.0, success_chance + event["chance_bonus"])  # Cap at 100%
                event_text = f"⭐ {event_text}"
            elif "chance_penalty" in event:
                success_chance = max(0.05, success_chance - event["chance_penalty"])  # Minimum 5% chance
                event_text = f"⚠️ {event_text}"
            
            # Apply currency modifiers
            if "currency_bonus" in event:
                await bank.deposit_credits(ctx.author, event["currency_bonus"])
                event_text += f" (+{event['currency_bonus']} {currency_name})"
            elif "currency_penalty" in event:
                await bank.withdraw_credits(ctx.author, event["currency_penalty"])
                event_text += f" (-{event['currency_penalty']} {currency_name})"
            
            await ctx.send(event_text)
            await asyncio.sleep(3)

            roll = random.random()

            # Attempt escape
            if roll < success_chance:
                # Success! Clear jail time
                await self.config.member(ctx.author).jail_until.set(0)
                await self.config.member(ctx.author).attempted_jailbreak.set(False)  # Reset jailbreak attempt when successful
                
                # Double check jail time is cleared
                remaining = await self.get_jail_time_remaining(ctx.author)
                if remaining > 0:
                    await ctx.send(_("Jail time not properly cleared! Remaining: {}").format(format_cooldown_time(remaining)))
                    # Force clear it
                    await self.config.member(ctx.author).jail_until.set(0)
                
                # Create success embed
                embed = discord.Embed(
                    title="🔓 Successful Jailbreak!",
                    description=_(scenario['success_text']).format(user=ctx.author.mention),
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="🎲 Final Escape Chance",
                    value=f"{success_chance:.1%}",
                    inline=True
                )
                await ctx.send(embed=embed)
            else:
                # Failed - double the remaining sentence
                remaining_time = await self.get_jail_time_remaining(ctx.author)
                added_time = remaining_time  # This is how much we're adding
                
                # Get current jail end time and add the remaining time again
                current_jail_until = await self.config.member(ctx.author).jail_until()
                new_jail_until = current_jail_until + added_time
                await self.config.member(ctx.author).jail_until.set(new_jail_until)
                
                # Create fail embed
                embed = discord.Embed(
                    title="⛓️ Failed Jailbreak!",
                    description=_(scenario['fail_text']).format(user=ctx.author.mention),
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="⚖️ Penalty",
                    value=f"Your sentence has been doubled! (+{format_cooldown_time(added_time)})",
                    inline=True
                )
                embed.add_field(
                    name="🎲 Final Escape Chance",
                    value=f"{success_chance:.1%}",
                    inline=True
                )
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(_("An error occurred while processing your jailbreak attempt. Please try again. Error: {}").format(str(e)))

    @crime.command(name="leaderboard", aliases=["lb"])
    @commands.guild_only()
    async def crime_leaderboard(self, ctx: commands.Context):
        """View the server's crime leaderboard."""
        
        stats = {
            "total_credits_earned": f"💰 __Most {await bank.get_currency_name(ctx.guild)} Earned__",
            "total_successful_crimes": "✅ __Most Successful Crimes__",
            "total_failed_crimes": "❌ __Most Failed Crimes__",
            "total_stolen_from": f"🦹 __Most {await bank.get_currency_name(ctx.guild)} Stolen__",
            "largest_heist": "💎 __Largest Heist__",
            "total_fines_paid": "💸 __Most Fines Paid__"
        }
        
        # Get all member data
        all_members = await self.config.all_members(ctx.guild)
        if not all_members:
            return await ctx.send("No crime statistics found for this server!")

        embed = discord.Embed(
            title="🏆 Crime Leaderboard - Hall of Infamy",
            description="The most notorious criminals in the server",
            color=await ctx.embed_color()
        )
        
        # Medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        # Process each stat
        for stat_key, title in stats.items():
            # Sort members by the current stat
            sorted_members = sorted(
                all_members.items(),
                key=lambda x: x[1].get(stat_key, 0),
                reverse=True
            )[:3]  # Top 3
            
            if not sorted_members:
                continue
                
            # Build the field value
            field_lines = []
            for i, (member_id, data) in enumerate(sorted_members):
                member = ctx.guild.get_member(member_id)
                if member is None:
                    continue
                    
                value = data.get(stat_key, 0)
                
                # Format value based on stat type
                if stat_key in ["total_credits_earned", "total_stolen_from", "total_fines_paid", "largest_heist"]:
                    value_str = f"{humanize_number(value)} credits"
                else:
                    value_str = str(value)
                    
                field_lines.append(f"{medals[i]} **{member.display_name}** • {value_str}")
            
            if field_lines:
                embed.add_field(
                    name=title,
                    value="\n".join(field_lines),
                    inline=False
                )
        
        # Add footer with timestamp
        embed.set_footer(text=f"Updated")
        embed.timestamp = datetime.now()
        
        await ctx.send(embed=embed)

    @commands.group(name="crimeset")
    @commands.admin_or_permissions(administrator=True)
    async def crime_set(self, ctx: commands.Context):
        """Configure crime settings
        
        Commands:
        - success_rate: Set success rate for a crime (0.0 to 1.0)
        - reward: Set min/max reward for a crime
        - cooldown: Set cooldown duration in seconds
        - jailtime: Set jail time duration in seconds
        - fine: Set fine multiplier for a crime
        - global: Configure global settings
        """
        pass

    @crime_set.command(name="success_rate")
    async def set_success_rate(
            self, ctx: commands.Context, crime_type: str, rate: float
        ):
        """Set the success rate for a crime type (0.0 to 1.0)"""
        if rate < 0 or rate > 1:
            await ctx.send(_("Success rate must be between 0.0 and 1.0"))
            return
            
        async with self.config.guild(ctx.guild).crime_options() as crime_options:
            if crime_type not in crime_options:
                await ctx.send(_("Invalid crime type!"))
                return
                
            crime_options[crime_type]["success_rate"] = rate
            
        await ctx.send(_("Success rate for {crime_type} set to {rate}").format(
            crime_type=crime_type,
            rate=rate
        ))

    @crime_set.command(name="reward")
    async def set_reward(
            self, ctx: commands.Context, crime_type: str, min_reward: int, max_reward: int
        ):
        """Set the reward range for a crime type"""
        if min_reward < 0 or max_reward < min_reward:
            await ctx.send(_("Invalid reward range!"))
            return
            
        async with self.config.guild(ctx.guild).crime_options() as crime_options:
            if crime_type not in crime_options:
                await ctx.send(_("Invalid crime type!"))
                return
                
            crime_options[crime_type]["min_reward"] = min_reward
            crime_options[crime_type]["max_reward"] = max_reward
            
        await ctx.send(_("Reward range for {crime_type} set to {min_reward}-{max_reward}").format(
            crime_type=crime_type,
            min_reward=min_reward,
            max_reward=max_reward
        ))

    @crime_set.command(name="cooldown")
    async def set_cooldown(
            self, ctx: commands.Context, crime_type: str, cooldown: int
        ):
        """Set the cooldown for a crime type (in seconds)"""
        if cooldown < 0:
            await ctx.send(_("Cooldown must be positive!"))
            return
            
        async with self.config.guild(ctx.guild).crime_options() as crime_options:
            if crime_type not in crime_options:
                await ctx.send(_("Invalid crime type!"))
                return
                
            crime_options[crime_type]["cooldown"] = cooldown
            
        await ctx.send(_("Cooldown for {crime_type} set to {time_remaining}").format(
            crime_type=crime_type,
            time_remaining=format_cooldown_time(cooldown)
        ))

    @crime_set.command(name="jailtime")
    async def set_jail_time(
            self, ctx: commands.Context, crime_type: str, jail_time: int
        ):
        """Set the jail time for a crime type (in seconds)"""
        if jail_time < 0:
            await ctx.send(_("Jail time must be positive!"))
            return
            
        async with self.config.guild(ctx.guild).crime_options() as crime_options:
            if crime_type not in crime_options:
                await ctx.send(_("Invalid crime type!"))
                return
                
            crime_options[crime_type]["jail_time"] = jail_time
            
        await ctx.send(_("Jail time for {crime_type} set to {time_remaining}").format(
            crime_type=crime_type,
            time_remaining=format_cooldown_time(jail_time)
        ))

    @crime_set.command(name="fine")
    async def set_fine_multiplier(
            self, ctx: commands.Context, crime_type: str, multiplier: float
        ):
        """Set the fine multiplier for a crime type"""
        if multiplier < 0:
            await ctx.send(_("Fine multiplier must be positive!"))
            return
            
        async with self.config.guild(ctx.guild).crime_options() as crime_options:
            if crime_type not in crime_options:
                await ctx.send(_("Invalid crime type!"))
                return
                
            crime_options[crime_type]["fine_multiplier"] = multiplier
            
        await ctx.send(_("Fine multiplier for {crime_type} set to {multiplier}").format(
            crime_type=crime_type,
            multiplier=multiplier
        ))

    @crime_set.command(name="reload_defaults")
    @commands.admin_or_permissions(administrator=True)
    async def reload_crime_defaults(self, ctx: commands.Context):
        """Reload the default crime settings for this guild.
        
        This will update all crime options to match the defaults in data.py.
        Warning: This will overwrite any custom settings!
        """
        from .data import CRIME_TYPES
        
        # Update crime options with defaults
        await self.config.guild(ctx.guild).crime_options.set(CRIME_TYPES.copy())
        
        await ctx.send("✅ Crime settings have been reloaded from defaults!")

    @crime_set.group(name="global")
    async def crime_set_global(self, ctx: commands.Context):
        """Configure global crime settings
        
        Commands:
        - bailcost: Set bail cost multiplier
        - togglebail: Enable/disable the bail system
        - view: View all current settings
        """
        pass

    @crime_set_global.command(name="bailcost")
    async def set_bail_multiplier(
            self, ctx: commands.Context, multiplier: float
        ):
        """Set the bail cost multiplier"""
        if multiplier < 0:
            await ctx.send(_("Bail cost multiplier must be positive!"))
            return
            
        async with self.config.guild(ctx.guild).global_settings() as settings:
            settings["bail_cost_multiplier"] = multiplier
            
        await ctx.send(_("Bail cost multiplier set to {multiplier}").format(
            multiplier=multiplier
        ))

    @crime_set_global.command(name="togglebail")
    async def toggle_bail(self, ctx: commands.Context, enabled: bool):
        """Enable or disable the bail system"""
        async with self.config.guild(ctx.guild).global_settings() as settings:
            settings["allow_bail"] = enabled
            
        if enabled:
            await ctx.send(_("Bail system enabled!"))
        else:
            await ctx.send(_("Bail system disabled!"))

    @crime_set_global.command(name="view")
    async def view_settings(self, ctx: commands.Context):
        """View all crime settings"""
        # Get settings
        crime_options = await self.config.guild(ctx.guild).crime_options()
        global_settings = await self.config.guild(ctx.guild).global_settings()
        
        # Build settings message
        settings_lines = [
            _("🌐 **Global Settings**:"),
            _("  • Bail System: {enabled}").format(enabled=_("Enabled") if global_settings["allow_bail"] else _("Disabled")),
            _("  • Bail Cost Multiplier: {multiplier}").format(multiplier=global_settings["bail_cost_multiplier"]),
            _("  • Min Steal Balance: {amount}").format(amount=global_settings["min_steal_balance"]),
            _("  • Max Steal Amount: {amount}").format(amount=global_settings["max_steal_amount"]),
            _("  • Notify Cost: {amount}").format(amount=global_settings.get("notify_cost", 0)),
            _("  • Notify Cost System: {enabled}").format(enabled=_("Enabled") if global_settings.get("notify_cost_enabled", False) else _("Disabled")),
            "",
            _("🎯 **Crime Settings**:")
        ]
        
        for crime_type, data in crime_options.items():
            if not data["enabled"]:
                continue
                
            settings_lines.extend([
                f"\n**{crime_type.title()}**:",
                _("  • Success Rate: {rate}").format(rate=data["success_rate"]),
                _("  • Reward: {min_reward}-{max_reward}").format(
                    min_reward=data["min_reward"],
                    max_reward=data["max_reward"]
                ),
                _("  • Cooldown: {time_remaining}").format(time_remaining=format_cooldown_time(data["cooldown"])),
                _("  • Jail Time: {time_remaining}").format(time_remaining=format_cooldown_time(data["jail_time"])),
                _("  • Fine Multiplier: {multiplier}").format(multiplier=data["fine_multiplier"])
            ])
            
        await ctx.send(box("\n".join(settings_lines)))

    @crime.command(name="notify")
    async def toggle_jail_notify(self, ctx: commands.Context):
        """Toggle whether you want to be pinged when your jail sentence is over.
        
        If enabled in server settings, this may cost credits to unlock.
        Use the command to see the current cost.
        """
        # Get settings
        settings = await self.config.guild(ctx.guild).global_settings()
        member_data = await self.config.member(ctx.author).all()
        
        # If notifications are already enabled, just toggle them off
        if member_data.get("notify_on_release", False):
            async with self.config.member(ctx.author).all() as member_data:
                member_data["notify_on_release"] = False
            
            embed = discord.Embed(
                title="🔕 Jail Release Notifications",
                description="Notifications have been disabled.\n\nYou will no longer be pinged when your jail sentence is over.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Check if cost system is enabled
        if settings.get("notify_cost_enabled", False):
            cost = settings.get("notify_cost", 0)
            
            # Create view with unlock button
            class UnlockView(discord.ui.View):
                def __init__(self, ctx, cost):
                    super().__init__(timeout=30.0)
                    self.ctx = ctx
                    self.cost = cost
                    self.value = None
                    
                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user.id == self.ctx.author.id
                
                @discord.ui.button(label=f"Unlock for {cost:,} credits", style=discord.ButtonStyle.success, emoji="🔔")
                async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
                    # Check if user can afford
                    if not await bank.can_spend(interaction.user, self.cost):
                        await interaction.response.send_message(
                            f"❌ You don't have enough credits! This costs {self.cost:,} {await bank.get_currency_name(interaction.guild)}.",
                            ephemeral=True
                        )
                        return
                        
                    # Charge the user
                    await bank.withdraw_credits(interaction.user, self.cost)
                    
                    # Get new balance
                    new_balance = await bank.get_balance(interaction.user)
                    currency_name = await bank.get_currency_name(interaction.guild)
                    
                    # Enable notifications
                    async with self.ctx.cog.config.member(interaction.user).all() as member_data:
                        member_data["notify_on_release"] = True
                    
                    # Send success message
                    embed = discord.Embed(
                        title="🔔 Jail Release Notifications",
                        description=f"Notifications have been enabled!\n\n"
                                  f"You paid {self.cost:,} {currency_name} to unlock this feature.\n"
                                  f"You will now be pinged when your jail sentence is over.",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=f"New balance: {new_balance:,} {currency_name}")
                    await interaction.response.send_message(embed=embed)
                    self.value = True
                    self.stop()
                    
                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
                async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                    embed = discord.Embed(
                        title="❌ Unlock Cancelled",
                        description="You decided not to unlock notifications.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed)
                    self.value = False
                    self.stop()
            
            # Send prompt with unlock button
            currency_name = await bank.get_currency_name(ctx.guild)
            embed = discord.Embed(
                title="🔔 Unlock Jail Release Notifications",
                description=f"This feature costs **{cost:,} {currency_name}** to unlock.\n\n"
                           f"Once unlocked, you will be pinged in the channel where you were jailed when your sentence is over.\n"
                           f"You can disable notifications at any time by using this command again.",
                color=discord.Color.blue()
            )
            
            view = UnlockView(ctx, cost)
            view.message = await ctx.send(embed=embed, view=view)
            
            # Wait for response
            await view.wait()
            
            # Disable buttons after timeout
            for child in view.children:
                child.disabled = True
            try:
                await view.message.edit(view=view)
            except discord.NotFound:
                pass
                
        else:
            # If cost system is disabled, just toggle notifications on
            async with self.config.member(ctx.author).all() as member_data:
                member_data["notify_on_release"] = True
            
            embed = discord.Embed(
                title="🔔 Jail Release Notifications",
                description="Notifications have been enabled!\n\nYou will now be pinged when your jail sentence is over.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

    @crime_set_global.command(name="notifycost")
    async def set_notify_cost(self, ctx: commands.Context, cost: int):
        """Set the cost to unlock jail release notifications.
        
        Parameters
        ----------
        cost : int
            The cost in credits to unlock notifications. Set to 0 to make it free.
        """
        if cost < 0:
            await ctx.send(_("Cost must be positive!"))
            return
            
        async with self.config.guild(ctx.guild).global_settings() as settings:
            settings["notify_cost"] = cost
            
        if cost == 0:
            await ctx.send(_("Jail release notifications are now free to unlock!"))
        else:
            await ctx.send(_("Jail release notifications now cost {cost} credits to unlock!").format(cost=cost))

    @crime_set_global.command(name="togglenotifycost")
    async def toggle_notify_cost(self, ctx: commands.Context, enabled: bool):
        """Enable or disable the notification unlock cost.
        
        Parameters
        ----------
        enabled : bool
            True to require payment to unlock notifications, False to make it free.
        """
        async with self.config.guild(ctx.guild).global_settings() as settings:
            settings["notify_cost_enabled"] = enabled
            
        if enabled:
            cost = settings.get("notify_cost", 0)
            await ctx.send(_("Jail release notifications now require {cost} credits to unlock!").format(cost=cost))
        else:
            await ctx.send(_("Jail release notifications are now free to unlock!"))

    async def send_to_jail(self, member: discord.Member, jail_time: int, channel: discord.TextChannel = None):
        """Send a member to jail."""
        async with self.config.member(member).all() as member_data:
            member_data["jail_until"] = int(time.time()) + jail_time
            member_data["attempted_jailbreak"] = False  # Reset jailbreak attempt when jailed
            
            # Store the channel ID where they were jailed if provided
            if channel:
                member_data["jail_channel"] = channel.id
            
            # If notifications are enabled, schedule a notification
            if member_data.get("notify_on_release", False):
                asyncio.create_task(self._schedule_release_notification(member, jail_time))
    
    async def _schedule_release_notification(self, member: discord.Member, jail_time: int):
        """Schedule a notification for when a member's jail sentence is over."""
        await asyncio.sleep(jail_time)
        
        # Double check they're actually out (in case sentence was extended)
        remaining = await self.get_jail_time_remaining(member)
        if remaining <= 0:
            try:
                # Only send if they still have notifications enabled
                member_data = await self.config.member(member).all()
                if member_data.get("notify_on_release", False):
                    # Try to send to the channel/thread they were jailed in
                    if "jail_channel" in member_data:
                        channel_id = member_data["jail_channel"]
                        # First try to get it as a thread
                        channel = member.guild.get_thread(channel_id)
                        # If not a thread, try as a regular channel
                        if channel is None:
                            channel = member.guild.get_channel(channel_id)
                            
                        if channel:
                            await channel.send(f"🔔 {member.mention} Your jail sentence is over! You're now free to commit crimes again.")
                            return
                    
                    # Fallback to DM if channel not found or not stored
                    await member.send(f"🔔 Your jail sentence is over! You're now free to commit crimes again.")
            except (discord.Forbidden, discord.HTTPException):
                pass  # Ignore if we can't send the message

    @crime.command(name="jail")
    @commands.admin_or_permissions(administrator=True)
    async def manual_jail(self, ctx: commands.Context, user: discord.Member, minutes: int):
        """Manually put a user in jail.

        Parameters
        ----------
        user : discord.Member
            The user to jail
        minutes : int
            Number of minutes to jail them for
        """
        try:
            if minutes <= 0:
                await ctx.send("❌ Jail time must be positive!")
                return

            # Convert minutes to seconds
            jail_time = minutes * 60

            # Send user to jail with the current channel
            await self.send_to_jail(user, jail_time, ctx.channel)

            embed = discord.Embed(
                title="⛓️ Manual Jail",
                description=f"{user.mention} has been jailed by {ctx.author.mention}!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="⏰ Sentence Duration",
                value=format_cooldown_time(jail_time),
                inline=True
            )
            embed.add_field(
                name="📅 Release Time",
                value=f"<t:{int(time.time() + jail_time)}:R>",
                inline=True
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"An error occurred while jailing the user: {str(e)}")
