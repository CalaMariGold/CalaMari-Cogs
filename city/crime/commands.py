"""Commands for the crime system."""

from redbot.core import commands, bank
from redbot.core.utils.chat_formatting import box, humanize_number
from redbot.core.i18n import Translator
import discord
import random
import time
import asyncio
from .scenarios import get_random_scenario, get_random_jailbreak_scenario
from .views import CrimeListView, BailView, CrimeView, TargetSelectionView, CrimeButton, MainMenuView, BlackmarketView, InventoryView, AddScenarioModal
from .data import CRIME_TYPES, DEFAULT_GUILD, DEFAULT_MEMBER
from .blackmarket import BLACKMARKET_ITEMS
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
        """Access the crime system.
        
        If no subcommand is provided, shows the main menu with all available actions.
        """
        try:
            # Get member data
            member_data = await self.config.member(ctx.author).all()
            
            # Get jail status
            jail_remaining = await self.get_jail_time_remaining(ctx.author)
            status = "⛓️ In jail" if jail_remaining > 0 else "✅ Free"
            
            # Create embed
            embed = discord.Embed(
                title="🌃 Welcome to the Criminal Underworld",
                description=(
                    "The city never sleeps, and neither do its criminals. What kind of trouble are you looking to get into today?\n\n"
                    "Choose your next move wisely..."
                ),
                color=discord.Color.dark_red()
            )
            
            # Add criminal record field
            embed.add_field(
                name="__Your Criminal Record__",
                value=(
                    f"🦹 Current Status: {status}\n"
                    f"💰 Lifetime Earnings: {humanize_number(member_data['total_credits_earned'])} {await bank.get_currency_name(ctx.guild)}\n"
                    f"✅ Successful Crimes: {member_data['total_successful_crimes']}\n"
                    f"❌ Failed Attempts: {member_data['total_failed_crimes']}\n"
                    f"🏆 Largest Heist: {humanize_number(member_data['largest_heist'])} {await bank.get_currency_name(ctx.guild)}"
                ),
                inline=False
            )
            
            # Create and send view
            view = MainMenuView(self, ctx)
            view.message = await ctx.send(embed=embed, view=view)
            
            # Initialize menu options
            await view.initialize_menu()
            
        except Exception as e:
            await ctx.send(f"An error occurred while opening the crime menu: {str(e)}")

    @crime.command(name="commit")
    async def crime_commit(self, ctx: commands.Context):
        """Choose a crime to commit using an interactive menu
        
        Available crimes:
        • 🧤 Pickpocket: Low risk, target users for small rewards
        • 🔪 Mugging: Medium risk, target users for medium rewards
        • 🏪 Store Robbery: Medium risk, no target needed
        • 🏛 Bank Heist: High risk, high rewards
        • 🎲 Random Crime: Random risk and rewards
        
        Each crime has:
        • Color-coded risk levels (green=low, blue=medium, red=high)
        • Success rates shown before committing
        • Cooldown periods between attempts
        • Fines and jail time if caught
        
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
                        name=f"{get_crime_emoji(crime_type)} __**{crime_type.replace('_', ' ').title()}**__",
                        value=description,
                        inline=True
                    )
                    embed.add_field(
                        name=f"{get_crime_emoji(next_crime_type)} __**{next_crime_type.replace('_', ' ').title()}**__",
                        value=next_description,
                        inline=True
                    )
                    # Add empty field to force next pair to start on new line
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
                else:
                    # Add single crime if no pair
                    embed.add_field(
                        name=f"{get_crime_emoji(crime_type)} __**{crime_type.replace('_', ' ').title()}**__",
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
        """View current jail status, cooldowns, and other active states
        
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
                title="🦹‍♂️ Criminal Status",
                description=f"Current status for {target.mention}",
                color=await ctx.embed_color()
            )
            
            # Set thumbnail to user's avatar
            embed.set_thumbnail(url=target.display_avatar.url)
            
            # Check jail status
            remaining_jail = await self.get_jail_time_remaining(target)
            if remaining_jail > 0:
                # Check if user has reduced sentence perk
                has_reducer = "jail_reducer" in member_data.get("purchased_perks", [])
                
                if has_reducer:
                    # Calculate original time (current time is after 20% reduction)
                    original_time = int(remaining_jail / 0.8)  # Reverse the 20% reduction
                    jail_text = f"🔒 In jail for ~~{format_cooldown_time(original_time, include_emoji=False)}~~ → {format_cooldown_time(remaining_jail, include_emoji=False)} (-20%)"
                else:
                    jail_text = f"🔒 In jail for {format_cooldown_time(remaining_jail)}"
                
                embed.add_field(
                    name="⚖️ __Jail Status__",
                    value=jail_text,
                    inline=False
                )
                
                # Show if they've attempted jailbreak this sentence
                if member_data.get("attempted_jailbreak", False):
                    embed.add_field(
                        name="🔓 __Jailbreak Status__",
                        value="❌ Already attempted this sentence",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="⚖️ __Jail Status__",
                    value="🆓 Not in jail",
                    inline=False
                )
            
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
            
            # Add notification status
            notify_on_release = member_data.get("notify_on_release", False)
            notify_unlocked = member_data.get("notify_unlocked", False)
            has_reducer = "jail_reducer" in member_data.get("purchased_perks", [])
            
            if notify_unlocked or has_reducer:
                status_lines = []
                if notify_unlocked:
                    status_lines.append("🔔 Notifications " + ("enabled" if notify_on_release else "disabled"))
                if has_reducer:
                    status_lines.append("⚖️ Reduced Sentence (-20% jail time)")
                
                embed.add_field(
                    name="🔰 __Active Perks__",
                    value="\n".join(status_lines),
                    inline=True
                )
            
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
            await ctx.send(_("An error occurred while retrieving the status. Please try again. Error: {}").format(str(e)))
            
    @crime.command(name="stats")
    async def crime_stats(self, ctx: commands.Context, user: discord.Member = None):
        """View detailed crime statistics and financial impact
        
        Parameters
        ----------
        user : discord.Member, optional
            The user to check stats for. If not provided, shows your own stats."""
        try:
            # Get member data
            target = user or ctx.author
            member_data = await self.config.member(target).all()
            currency_name = await bank.get_currency_name(ctx.guild)

            # Create stats embed
            embed = discord.Embed(
                title="📊 Criminal Statistics",
                description=f"Detailed statistics for {target.mention}",
                color=await ctx.embed_color()
            )
            
            # Set thumbnail to user's avatar
            embed.set_thumbnail(url=target.display_avatar.url)
            
            # Add crime statistics in two columns
            stats_left = [
                f"**{currency_name} Earned:** {humanize_number(member_data['total_credits_earned'])}",
                f"**Crimes:** ✅ {member_data['total_successful_crimes']} | ❌ {member_data['total_failed_crimes']}",
                f"**{currency_name} Stolen:** {humanize_number(member_data['total_stolen_from'])}",
                f"**Largest Heist:** {humanize_number(member_data['largest_heist'])}"
            ]
            
            # Calculate success rate
            total_crimes = member_data['total_successful_crimes'] + member_data['total_failed_crimes']
            success_rate = (member_data['total_successful_crimes'] / total_crimes * 100) if total_crimes > 0 else 0
            
            stats_right = [
                f"**Total Fines:** {humanize_number(member_data['total_fines_paid'])}",
                f"**Total Bail:** {humanize_number(member_data['total_bail_paid'])}",
                f"**{currency_name} Lost:** {humanize_number(member_data['total_stolen_by'])}",
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
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            await ctx.send(_("An error occurred while retrieving the stats. Please try again. Error: {}").format(str(e)))

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
            bail_cost = int(settings.get("bail_cost_multiplier", 1.5) * (jail_time / 60))  # Convert seconds to minutes
            
            # Check if user can afford bail
            if not await bank.can_spend(ctx.author, bail_cost):
                await ctx.send(
                    _("💵❌You don't have enough {currency} to pay the bail amount of {amount}!").format(
                        currency=await bank.get_currency_name(ctx.guild),
                        amount=bail_cost
                    )
                )
                return
                
            # Get current balance
            current_balance = await bank.get_balance(ctx.author)
            currency_name = await bank.get_currency_name(ctx.guild)
            
            # Get member data for perk check
            member_data = await self.config.member(ctx.author).all()
            
            # Create embed for bail prompt
            embed = discord.Embed(
                title="💰 Bail Payment Available",
                description=(
                    "You can pay bail to get out of jail immediately, or wait out your sentence.\n\n"
                    f"**Time Remaining:** {format_cooldown_time(jail_time, include_emoji=False)}"
                    + (" (Reduced by 20%)" if "jail_reducer" in member_data.get("purchased_perks", []) else "") + "\n"
                    f"**Bail Cost:** {bail_cost:,} {currency_name}\n"
                    f"**Current Balance:** {current_balance:,} {currency_name}\n\n"
                ),
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            
            # Send bail prompt
            view = BailView(self, ctx, bail_cost, jail_time)
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
        
        Failed attempt doubles jail time!
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

            # Get 2-4 random events
            num_events = random.randint(2, 4)
            selected_events = random.sample(scenario['events'], num_events)
            
            # Apply events in sequence
            for event in selected_events:
                event_text = event['text']
                # Format event text with currency name
                currency_name = await bank.get_currency_name(ctx.guild)
                event_text = event_text.format(currency=currency_name)
                
                # Apply chance modifiers and log them
                if "chance_bonus" in event:
                    success_chance = min(1.0, success_chance + event["chance_bonus"])  # Cap at 100%
                    event_text = f"⭐ {event_text}"
                elif "chance_penalty" in event:
                    success_chance = max(0.05, success_chance - event["chance_penalty"])  # Minimum 5% chance
                    event_text = f"⚠️ {event_text}"
                
                # Apply currency modifiers
                if "currency_bonus" in event:
                    await bank.deposit_credits(ctx.author, event["currency_bonus"])
                    event_text += f"⭐ (+{event['currency_bonus']} {currency_name})"
                elif "currency_penalty" in event:
                    await bank.withdraw_credits(ctx.author, event["currency_penalty"])
                    event_text += f"⚠️ (-{event['currency_penalty']} {currency_name})"
                
                await ctx.send(event_text)
                await asyncio.sleep(3.5)

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
                
                # Format the time for penalty calculation
                minutes = remaining_time // 60
                seconds = remaining_time % 60
                new_minutes = (remaining_time * 2) // 60
                new_seconds = (remaining_time * 2) % 60
                
                embed.add_field(
                    name="⚖️ Penalty",
                    value=f"Your sentence has been doubled!\n ({minutes}m {seconds}s * 2 = ⏰ {new_minutes}m {new_seconds}s)",
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
        
        # Get guild's currency name
        currency_name = await bank.get_currency_name(ctx.guild)
        
        stats = {
            "earnings": {
                "title": f"💰 __Most {currency_name} Earned__",
                "field": "total_credits_earned",
                "format": "credits"
            },
            "crimes": {
                "title": "🦹 __Crime Success/Fails__",
                "fields": ["total_successful_crimes", "total_failed_crimes"],
                "format": "counts"
            },
            "stolen": {
                "title": f"💎 __Stolen/Lost {currency_name}__",
                "fields": ["total_stolen_from", "total_stolen_by"],
                "format": "credits"
            },
            "largest_heist": {
                "title": f"🏆 __Largest Heist__",
                "field": "largest_heist",
                "format": "credits"
            },
            "fines": {
                "title": f"💸 __Most Fines/Bail Paid__",
                "fields": ["total_fines_paid", "total_bail_paid"],
                "format": "credits"
            }
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
        
        # Process each stat category
        field_count = 0  # Track number of non-empty fields
        for stat_info in stats.values():
            if "fields" in stat_info:  # Combined stats
                # Sort members by the sum of both fields
                sorted_members = sorted(
                    all_members.items(),
                    key=lambda x: sum(x[1].get(field, 0) for field in stat_info["fields"]),
                    reverse=True
                )[:3]
                
                if not sorted_members:
                    continue
                    
                field_lines = []
                for i, (member_id, data) in enumerate(sorted_members):
                    member = ctx.guild.get_member(member_id)
                    if member is None:
                        continue
                        
                    if stat_info["format"] == "credits":
                        if stat_info["title"].startswith("💸"):  # Fines category
                            total_paid = data.get(stat_info['fields'][0], 0) + data.get(stat_info['fields'][1], 0)
                            field_lines.append(f"{medals[i]} **{member.display_name}** • {humanize_number(total_paid)} {currency_name}")
                        elif stat_info["title"].startswith("💎"):  # Stolen/Lost category
                            value1 = humanize_number(data.get(stat_info['fields'][0], 0))
                            value2 = humanize_number(data.get(stat_info['fields'][1], 0))
                            field_lines.append(f"{medals[i]} **{member.display_name}** • {value1} / {value2}")
                        else:
                            value1 = f"{humanize_number(data.get(stat_info['fields'][0], 0))} {currency_name}"
                            value2 = f"{humanize_number(data.get(stat_info['fields'][1], 0))} {currency_name}"
                            field_lines.append(f"{medals[i]} **{member.display_name}** • {value1} / {value2}")
                    else:  # counts
                        wins = data.get(stat_info['fields'][0], 0)
                        fails = data.get(stat_info['fields'][1], 0)
                        field_lines.append(f"{medals[i]} **{member.display_name}** • {wins}w / {fails}f")
                
                if field_lines:
                    embed.add_field(
                        name=stat_info["title"],
                        value="\n".join(field_lines),
                        inline=True
                    )
                    field_count += 1
                    
                    # Add empty field only if we have an odd number of fields and it's not the last field
                    if field_count % 2 == 1 and field_count < len(stats):
                        embed.add_field(name="\u200b", value="\u200b", inline=True)
            else:  # Single stat
                sorted_members = sorted(
                    all_members.items(),
                    key=lambda x: x[1].get(stat_info["field"], 0),
                    reverse=True
                )[:3]
                
                if not sorted_members:
                    continue
                    
                field_lines = []
                for i, (member_id, data) in enumerate(sorted_members):
                    member = ctx.guild.get_member(member_id)
                    if member is None:
                        continue
                        
                    value = data.get(stat_info["field"], 0)
                    if stat_info["format"] == "credits":
                        value_str = f"{humanize_number(value)} {currency_name}"
                    else:
                        value_str = str(value)
                        
                    field_lines.append(f"{medals[i]} **{member.display_name}** • {value_str}")
                
                if field_lines:
                    embed.add_field(
                        name=stat_info["title"],
                        value="\n".join(field_lines),
                        inline=True
                    )
                    field_count += 1
                    
                    # Add empty field only if we have an odd number of fields and it's not the last field
                    if field_count % 2 == 1 and field_count < len(stats):
                        embed.add_field(name="\u200b", value="\u200b", inline=True)
        
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
            
        await ctx.send("\n".join(settings_lines))

    async def send_to_jail(self, member: discord.Member, jail_time: int, channel: discord.TextChannel = None):
        """Send a member to jail."""
        async with self.config.member(member).all() as member_data:
            # Check for reduced sentence perk
            if "jail_reducer" in member_data.get("purchased_perks", []):
                # Apply 20% reduction
                jail_time = int(jail_time * 0.8)  # 20% shorter sentence
            
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
            
            # Check if user has reduced sentence perk
            member_data = await self.config.member(user).all()
            has_reducer = "jail_reducer" in member_data.get("purchased_perks", [])
            if has_reducer:
                jail_time = int(jail_time * 0.8)  # 20% reduction

            # Send user to jail with the current channel
            await self.send_to_jail(user, jail_time, ctx.channel)

            embed = discord.Embed(
                title="⛓️ Manual Jail",
                description=f"{user.mention} has been jailed by {ctx.author.mention}!",
                color=discord.Color.red()
            )
            
            sentence_text = format_cooldown_time(jail_time)
            if has_reducer:
                sentence_text += " (Reduced by 20%)"
                
            embed.add_field(
                name="⏰ Sentence Duration",
                value=sentence_text,
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

    @crime.command(name="blackmarket")
    async def crime_blackmarket(self, ctx: commands.Context):
        """Browse the black market for special items and perks.
        
        Available items:
        • 🔔 Jail Release Notification - Get notified when released
        • ⚖️ Reduced Sentence - 20% shorter jail time
        • 🔓 Get Out of Jail Free - Instant release from jail
        • 🍀 Lucky Charm - Temporary crime success boost
        
        Use the dropdown menu to purchase items.
        Some items are permanent perks, others are consumable.
        """
        try:
            # Create embed
            embed = discord.Embed(
                title="🏴‍☠️ Black Market",
                description=(
                    "Welcome to the shadier side of the city...\n"
                    "Here you can find various items and perks to aid your criminal career.\n"
                    "Use the dropdown menu below to make a purchase."
                ),
                color=discord.Color.dark_purple()
            )
            
            # Add current balance
            balance = await bank.get_balance(ctx.author)
            currency_name = await bank.get_currency_name(ctx.guild)
            embed.add_field(
                name="💰 Your Balance",
                value=f"{balance:,} {currency_name}",
                inline=False
            )
            
            # Group items by type
            perks = []
            consumables = []
            
            for item_id, item in BLACKMARKET_ITEMS.items():
                if item["type"] == "perk":
                    perks.append(
                        f"{item['emoji']} **{item['name']}** - {item['cost']:,} {currency_name}\n"
                        f"↳ {item['description']}"
                    )
                else:
                    consumables.append(
                        f"{item['emoji']} **{item['name']}** - {item['cost']:,} {currency_name}\n"
                        f"↳ {item['description']}"
                    )
            
            # Add perks section
            if perks:
                embed.add_field(
                    name="🔒 Permanent Perks",
                    value="\n\n".join(perks),
                    inline=False
                )
            
            # Add consumables section
            if consumables:
                embed.add_field(
                    name="📦 Consumable Items",
                    value="\n\n".join(consumables),
                    inline=False
                )
            
            # Create and send view
            view = BlackmarketView(self, ctx)
            view.message = await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            await ctx.send(f"An error occurred while opening the black market: {str(e)}")

    @crime.command(name="inventory")
    async def view_inventory(self, ctx: commands.Context):
        """View your inventory of items and perks."""
        try:
            # Get member data
            member_data = await self.config.member(ctx.author).all()
            current_time = int(time.time())
            
            # Create embed
            embed = discord.Embed(
                title="🎒 Your Inventory",
                description="Use the dropdowns below to activate or sell your items.",
                color=discord.Color.blue()
            )
            
            # Add perks section
            perks = member_data.get("purchased_perks", [])
            if perks:
                perk_list = []
                for perk_id in perks:
                    perk = BLACKMARKET_ITEMS[perk_id]
                    perk_list.append(f"{perk['emoji']} **{perk['name']}**\n↳ {perk['description']}")
                embed.add_field(
                    name="🔒 Permanent Perks",
                    value="\n".join(perk_list),
                    inline=False
                )
            
            # Add active items section
            active_items = member_data.get("active_items", {})
            if active_items:
                active_list = []
                for item_id, status in active_items.items():
                    item = BLACKMARKET_ITEMS[item_id]
                    
                    if "duration" in item:
                        end_time = status.get("end_time", 0)
                        if end_time > current_time:
                            remaining = end_time - current_time
                            hours = remaining // 3600
                            minutes = (remaining % 3600) // 60
                            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                            active_list.append(
                                f"{item['emoji']} **{item['name']}**\n↳ Time remaining: {time_str}"
                            )
                    else:
                        uses = status.get("uses", 0)
                        if uses > 0:
                            active_list.append(
                                f"{item['emoji']} **{item['name']}**\n↳ {uses} uses remaining"
                            )
                            
                if active_list:
                    embed.add_field(
                        name="📦 Items",
                        value="\n".join(active_list),
                        inline=False
                    )
            
            if not perks and not active_items:
                embed.description += "\n\n❌ Your inventory is empty! Visit the black market to purchase items."
            
            # Create and send view
            view = InventoryView(self, ctx)
            view.message = await ctx.send(embed=embed, view=view)
            
            # Initialize dropdowns
            await view.initialize_dropdowns()
            
        except Exception as e:
            await ctx.send(_("An error occurred while viewing your inventory: {}").format(str(e)))

    @crime_set.group(name="scenarios")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def crime_set_scenarios(self, ctx: commands.Context):
        """Manage custom random scenarios for this server.
        
        Commands:
        - add: Add a new custom scenario
        - list: List all custom scenarios
        - remove: Remove a custom scenario
        """
        pass

    @crime_set_scenarios.command(name="add")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def add_scenario(self, ctx: commands.Context):
        """Add a custom random scenario to the crime pool.
        
        This will guide you through creating a custom scenario by asking for:
        - Scenario name
        - Risk level (low, medium, high)
        - Attempt text
        - Success text (use {amount} and {currency} placeholders)
        - Fail text
        
        Custom scenarios are saved per server and persist through bot restarts.
        """
        # Start scenario creation process
        await ctx.send("Let's create a new random scenario! I'll ask you for each piece of information.")
        
        try:
            # Get scenario name
            await ctx.send("What would you like to name this scenario? (e.g. cookie_heist)")
            msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
            name = msg.content.lower()
            
            # Get risk level
            await ctx.send("What risk level should this be? (low, medium, or high)")
            while True:
                msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=30)
                risk = msg.content.lower()
                if risk not in ["low", "medium", "high"]:
                    await ctx.send("Please enter either 'low', 'medium', or 'high'.")
                else:
                    break
            
            # Get attempt text
            await ctx.send("Enter the attempt text (use {user} for the user's mention):")
            msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            attempt_text = msg.content
            
            # Get success text
            await ctx.send("Enter the success text (use {user} for the user's mention, {amount} for the reward amount, and {currency} for the currency name):")
            msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            success_text = msg.content
            
            # Get fail text
            await ctx.send("Enter the fail text (use {user} for the user's mention, {fine} for the fine amount, and {currency} for the currency name):")
            msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60)
            fail_text = msg.content
            
            # Set values based on risk level
            if risk == "low":
                success_rate = 0.7
                min_reward = 100
                max_reward = 300
                jail_time = 180
                fine_multiplier = 0.3
            elif risk == "medium":
                success_rate = 0.5
                min_reward = 300
                max_reward = 800
                jail_time = 300
                fine_multiplier = 0.4
            else:  # high
                success_rate = 0.3
                min_reward = 800
                max_reward = 2000
                jail_time = 600
                fine_multiplier = 0.5
                
            # Create new scenario
            new_scenario = {
                "name": name,
                "risk": risk,
                "min_reward": min_reward,
                "max_reward": max_reward,
                "success_rate": success_rate,
                "jail_time": jail_time,
                "fine_multiplier": fine_multiplier,
                "attempt_text": attempt_text,
                "success_text": success_text,
                "fail_text": fail_text
            }
            
            # Add to guild's custom scenarios
            async with self.config.guild(ctx.guild).custom_scenarios() as scenarios:
                scenarios.append(new_scenario)
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Custom Scenario Added!",
                description=f"Your scenario '{name}' has been added to this server's random crime pool.",
                color=discord.Color.green()
            )
            embed.add_field(name="Risk Level", value=risk.title(), inline=True)
            embed.add_field(name="Success Rate", value=f"{int(success_rate * 100)}%", inline=True)
            embed.add_field(name="Reward Range", value=f"{min_reward:,} - {max_reward:,}", inline=True)
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            await ctx.send("❌ Scenario creation timed out. Please try again.")

    @crime_set_scenarios.command(name="list")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def list_scenarios(self, ctx: commands.Context):
        """List all custom scenarios in this server."""
        custom_scenarios = await self.config.guild(ctx.guild).custom_scenarios()
        
        if not custom_scenarios:
            await ctx.send("This server has no custom scenarios.")
            return
        
        # Create embed to display scenarios
        embed = discord.Embed(
            title="📜 Custom Random Scenarios",
            description=f"This server has {len(custom_scenarios)} custom scenarios:",
            color=await ctx.embed_color()
        )
        
        for scenario in custom_scenarios:
            # Format success rate as percentage
            success_rate = int(scenario["success_rate"] * 100)
            
            # Create field content
            details = [
                f"**Risk Level:** {scenario['risk'].title()}",
                f"**Success Rate:** {success_rate}%",
                f"**Reward:** {scenario['min_reward']:,} - {scenario['max_reward']:,}",
                f"**Jail Time:** {scenario['jail_time']} seconds",
                f"**Fine Multiplier:** {scenario['fine_multiplier']}"
            ]
            
            embed.add_field(
                name=f"🎲 {scenario['name']}",
                value="\n".join(details),
                inline=False
            )
        
        await ctx.send(embed=embed)

    @crime_set_scenarios.command(name="remove")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def remove_scenario(self, ctx: commands.Context, scenario_name: str):
        """Remove a custom scenario by name.
        
        Example:
        - [p]crimeset scenarios remove cookie_heist
        """
        async with self.config.guild(ctx.guild).custom_scenarios() as scenarios:
            # Find scenario with matching name
            for i, scenario in enumerate(scenarios):
                if scenario["name"].lower() == scenario_name.lower():
                    removed = scenarios.pop(i)
                    await ctx.send(f"✅ Removed custom scenario: {removed['name']}")
                    return
            
            await ctx.send("❌ No custom scenario found with that name.")
