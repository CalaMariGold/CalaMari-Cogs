"""Views for the crime system."""

import discord
import random
from redbot.core import commands, bank
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_number
from typing import Optional, Tuple
from ..utils import calculate_stolen_amount, can_target_user
import asyncio
from .scenarios import get_random_scenario, get_crime_event, format_text

_ = Translator("Crime", __file__)

class CrimeButton(discord.ui.Button):
    """A button for committing crimes"""
    def __init__(self, style: discord.ButtonStyle, label: str, emoji: str, custom_id: str, disabled: bool = False):
        super().__init__(
            style=style,
            label=label,
            emoji=emoji,
            custom_id=custom_id,
            disabled=disabled
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button press"""
        if interaction.user.bot:
            return
            
        view: CrimeListView = self.view
        
        try:
            await interaction.response.defer()
            
            # Get crime data
            crime_type = self.custom_id
            crime_data = view.crime_options[crime_type]
            
            # Check if user is in jail
            jail_remaining = await view.cog.get_jail_time_remaining(interaction.user)
            if jail_remaining > 0:
                await interaction.channel.send(
                    _("⛓️ You're still in jail for {minutes}m {seconds}s! You can pay bail using `!crime bail` or jailbreak using `!crime jailbreak`").format(
                        minutes=jail_remaining // 60,
                        seconds=jail_remaining % 60
                    )
                )
                return
                
            # Check cooldown
            remaining = await view.cog.get_remaining_cooldown(interaction.user, crime_type)
            if remaining > 0:
                if remaining > 3600:  # If more than 1 hour
                    hours = remaining // 3600
                    minutes = (remaining % 3600) // 60
                    await interaction.channel.send(
                        _("⏳ You must wait {hours}h {minutes}m before attempting {crime_type} again!").format(
                            hours=hours,
                            minutes=minutes,
                            crime_type=crime_type.replace('_', ' ').title()
                        )
                    )
                else:
                    await interaction.channel.send(
                        _("⏳ You must wait {minutes}m {seconds}s before attempting {crime_type} again!").format(
                            minutes=remaining // 60,
                            seconds=remaining % 60,
                            crime_type=crime_type.replace('_', ' ').title()
                        )
                    )
                return
                
            # Get settings
            settings = await view.cog.config.guild(interaction.guild).global_settings()
            
            # Delete the crime list message since we're moving to confirmation
            # Only delete if we're past the cooldown and jail checks
            try:
                await view.message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            
            # If crime requires target, show target selection
            if crime_data.get("requires_target", False):
                target_view = TargetSelectionView(view.cog, interaction, crime_type, crime_data)
                message = await interaction.channel.send(
                    _("Choose your target:"),
                    view=target_view
                )
                target_view.message = message
                target_view.all_messages.append(message)  # Track message
            else:
                # Show confirmation for non-targeted crime
                crime_view = CrimeView(view.cog, interaction, crime_type, crime_data)
                
                # Format message based on crime type
                if crime_type == "random":
                    embed = discord.Embed(
                        title="🎲 Random Crime",
                        description="Are you feeling lucky?",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="📊 Success Rate", value="???", inline=True)
                    embed.add_field(name="💸 Potential Fine", value="???", inline=True)
                else:
                    embed = discord.Embed(
                        title=f"{crime_data.get('emoji', '🦹')} {crime_type.replace('_', ' ').title()}",
                        description="Your move, boss. You ready?",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="📊 Success Rate",
                        value=f"{int(crime_data['success_rate'] * 100)}%",
                        inline=True
                    )
                    embed.add_field(
                        name="💸 Potential Fine",
                        value=f"{int(crime_data['max_reward'] * crime_data['fine_multiplier']):,} {await bank.get_currency_name(interaction.guild)}",
                        inline=True
                    )
                
                message = await interaction.channel.send(
                    embed=embed,
                    view=crime_view
                )
                crime_view.message = message
                crime_view.all_messages = [message]  # Track message
                
        except Exception as e:
            await interaction.channel.send(
                _("An error occurred while processing your crime. Please try again. Error: {error}").format(
                    error=str(e)
                )
            )

class CrimeListView(discord.ui.View):
    """View for listing available crimes"""
    def __init__(self, cog, ctx: commands.Context, crime_options: dict):
        super().__init__(timeout=60)  # 1 minute timeout
        self.cog = cog
        self.ctx = ctx
        self.crime_options = crime_options
        self.message = None
        self.all_messages = []  # Track all messages
        
        # Add buttons for each crime
        for crime_type, data in crime_options.items():
            # Skip disabled crimes
            if not data.get("enabled", True):
                continue
            
            # Get button color based on risk
            style = discord.ButtonStyle.danger if data["risk"] == "high" else discord.ButtonStyle.primary if data["risk"] == "medium" else discord.ButtonStyle.success
            
            # Get crime emoji
            if crime_type == "pickpocket":
                crime_emoji = "🧤"
            elif crime_type == "mugging":
                crime_emoji = "🔪"
            elif crime_type == "rob_store":
                crime_emoji = "🏪"
            elif crime_type == "random":
                crime_emoji = "🎲"
            else:  # bank heist
                crime_emoji = "🏛"
            
            # Create button with proper name formatting
            button = CrimeButton(
                style=style,
                label=crime_type.replace('_', ' ').title(),
                emoji=crime_emoji,
                custom_id=crime_type,
                disabled=False  # Initially enable all buttons
            )
            self.add_item(button)
            
    async def update_button_states(self):
        """Update button states based on jail and cooldowns"""
        is_jailed = await self.cog.is_jailed(self.ctx.author)
        
        for item in self.children:
            if isinstance(item, CrimeButton):
                remaining = await self.cog.get_remaining_cooldown(self.ctx.author, item.custom_id)
                item.disabled = is_jailed or remaining > 0
        
        if self.message:
            await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the author that invoked the command to use the interaction"""
        return interaction.user.id == self.ctx.author.id

    async def on_timeout(self) -> None:
        """Handle view timeout"""
        try:
            for item in self.children:
                item.disabled = True
            if self.message:
                await self.message.delete()
        except (discord.NotFound, discord.HTTPException):
            pass

class CrimeView(discord.ui.View):
    """View for crime confirmation."""
    
    def __init__(self, cog, interaction: discord.Interaction, crime_type: str, crime_data: dict, target: Optional[discord.Member] = None):
        super().__init__(timeout=30)
        self.cog = cog
        self.interaction = interaction
        self.crime_type = crime_type
        self.crime_data = crime_data
        self.target = target
        self.message = None
        self.all_messages = []  # Track all messages
        self.scenario = None
        
    async def format_crime_message(self, success: bool, is_attempt: bool = False, **kwargs):
        """Format crime result message."""
        currency = await bank.get_currency_name(self.interaction.guild)
        
        if is_attempt and self.crime_type == "random":
            embed = discord.Embed(
                title="🎲 Random Crime",
                description="Are you feeling lucky?",
                color=discord.Color.greyple()
            )
            embed.add_field(name="📊 Success Rate", value="???", inline=True)
            embed.add_field(name="💸 Potential Fine", value="???", inline=True)
            return embed
            
        # Get success/fail messages based on crime type
        if success:
            embed = discord.Embed(
                title=f"{self.crime_data.get('emoji', '💰')} Successful {self.crime_type.replace('_', ' ').title()}!",
                color=discord.Color.green()
            )
            
            if self.crime_type == "random":
                embed.description = _(self.scenario["success_text"]).format(
                    user=self.interaction.user.mention,
                    amount=kwargs["reward"],
                    currency=currency
                )
            else:
                if self.target:
                    if self.crime_type == "pickpocket":
                        embed.description = f"🧤 {self.interaction.user.mention} successfully pickpocketed {self.target.mention}!"
                    elif self.crime_type == "mugging":
                        embed.description = f"🔪 {self.interaction.user.mention} successfully mugged {self.target.mention}!"
                else:
                    if self.crime_type == "pickpocket":
                        embed.description = f"🧤 {self.interaction.user.mention} successfully picked a pocket!"
                    elif self.crime_type == "mugging":
                        embed.description = f"🔪 {self.interaction.user.mention} successfully mugged someone!"
                    elif self.crime_type == "rob_store":
                        embed.description = f"🏪 {self.interaction.user.mention} successfully robbed the store!"
                    else:  # bank heist
                        embed.description = f"🏛 {self.interaction.user.mention} successfully pulled off a bank heist!"
                        
            # Add reward field
            embed.add_field(
                name="💰 Reward",
                value=f"{kwargs.get('reward', 0):,} {currency}",
                inline=False
            )
            
            # Add success rate if not random
            if self.crime_type != "random":
                embed.add_field(
                    name="📊 Success Rate",
                    value=f"{kwargs.get('rate', int(self.crime_data['success_rate'] * 100))}%",
                    inline=True
                )
            
            # Add credit changes field if any occurred
            if kwargs.get('credit_changes', 0) != 0:
                if kwargs['credit_changes'] > 0:
                    embed.add_field(
                        name="💰 Bonus Credits",
                        value=f"+{kwargs['credit_changes']:,} {currency}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="💸 Credit Losses",
                        value=f"{kwargs['credit_changes']:,} {currency}",
                        inline=True
                    )
            
            return embed
        else:
            embed = discord.Embed(
                title=f"👮 Failed {self.crime_type.replace('_', ' ').title()}!",
                color=discord.Color.red()
            )
            
            if self.crime_type == "random":
                embed.description = _(self.scenario["fail_text"]).format(
                    user=self.interaction.user.mention,
                    fine=kwargs["fine"],
                    currency=currency
                )
            else:
                if self.crime_type == "pickpocket":
                    if self.target:
                        embed.description = f"{self.interaction.user.mention} was caught trying to pickpocket {self.target.mention}!"
                    else:
                        embed.description = f"{self.interaction.user.mention} was caught with their hand in someone's pocket!"
                elif self.crime_type == "mugging":
                    if self.target:
                        embed.description = f"{self.interaction.user.mention} was caught trying to mug {self.target.mention}!"
                    else:
                        embed.description = f"{self.interaction.user.mention} was caught trying to mug someone!"
                elif self.crime_type == "rob_store":
                    embed.description = f"{self.interaction.user.mention} was caught trying to rob the store!"
                else:  # bank heist
                    embed.description = f"{self.interaction.user.mention} was caught trying to rob the bank!"
            
            # Add fine field
            if kwargs.get("fine", 0) > 0:
                embed.add_field(
                    name="💸 Fine",
                    value=f"{kwargs['fine']:,} {currency}",
                    inline=True
                )
            
            # Add jail time field
            if kwargs.get("jail_time", 0) > 0:
                jail_minutes = kwargs["jail_time"] // 60
                jail_seconds = kwargs["jail_time"] % 60
                embed.add_field(
                    name="⛓️ Jail Time",
                    value=f"{jail_minutes}m {jail_seconds}s",
                    inline=True
                )
            
            # Add success rate if not random
            if self.crime_type != "random":
                embed.add_field(
                    name="📊 Success Rate",
                    value=f"{kwargs.get('rate', int(self.crime_data['success_rate'] * 100))}%",
                    inline=True
                )
            
            # Add credit changes field if any occurred
            if kwargs.get('credit_changes', 0) != 0:
                if kwargs['credit_changes'] > 0:
                    embed.add_field(
                        name="💰 Bonus Credits",
                        value=f"+{kwargs['credit_changes']:,} {currency}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="💸 Credit Losses",
                        value=f"{kwargs['credit_changes']:,} {currency}",
                        inline=True
                    )
            
            return embed
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original user to use the view."""
        return interaction.user.id == self.interaction.user.id
        
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle errors in view interactions."""
        await interaction.channel.send(
            _("An error occurred while processing your crime. Please try again. Error: {error}").format(
                error=str(error)
            )
        )
        self.stop()
            
    async def on_timeout(self):
        """Handle view timeout"""
        try:
            # Disable all buttons
            for item in self.children:
                item.disabled = True
                
            # Try to update the message if it still exists
            if self.message:
                try:
                    await self.message.edit(view=self)
                    if not self.is_finished():
                        try:
                            msg = await self.message.channel.send(_("Crime timed out."))
                            self.all_messages.append(msg)
                        except discord.HTTPException:
                            pass
                except (discord.NotFound, discord.HTTPException):
                    pass
        except Exception:
            # Silently handle any other errors since the channel might not be available
            pass
        finally:
            self.stop()
            
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle crime confirmation"""
        if interaction.user.bot:
            return
            
        try:
            await interaction.response.defer()
            
            # Get settings
            settings = await self.cog.config.guild(interaction.guild).global_settings()
            
            # Double check cooldown
            remaining = await self.cog.get_remaining_cooldown(interaction.user, self.crime_type)
            if remaining > 0:
                msg = await interaction.channel.send(
                    _("⏳ You must wait {hours}h {minutes}m before attempting {crime_type} again!").format(
                        hours=remaining // 3600,
                        minutes=(remaining % 3600) // 60,
                        crime_type=self.crime_type
                    )
                )
                self.all_messages.append(msg)
                return
                
            # Check if user is jailed
            if await self.cog.is_jailed(interaction.user):
                remaining = await self.cog.get_jail_time_remaining(interaction.user)
                msg = await interaction.channel.send(
                    _("⛓️ You're still in jail for {minutes}m {seconds}s! You can pay bail using `!crime bail` or jailbreak using `!crime jailbreak`").format(
                        minutes=remaining // 60,
                        seconds=remaining % 60
                    )
                )
                self.all_messages.append(msg)
                return
                
            # For targeted crimes, check target's balance before attempting
            if self.target:
                try:
                    target_balance = await bank.get_balance(self.target)
                    min_required = max(settings.get("min_steal_balance", 100), self.crime_data["min_reward"])
                    
                    if target_balance < min_required:
                        msg = await interaction.channel.send(
                            _("Your target doesn't have enough {currency} to steal from! (Minimum: {min:,})").format(
                                currency=await bank.get_currency_name(interaction.guild),
                                min=min_required
                            )
                        )
                        self.all_messages.append(msg)
                        return
                except Exception as e:
                    await interaction.channel.send(
                        _("An error occurred while checking your target's balance. Please try again. Error: {error}").format(
                            error=str(e)
                        )
                    )
                    self.all_messages.append(msg)
                    return
                
            # Delete confirmation message and target selection message if it exists
            try:
                await self.message.delete()
                # Delete any previous messages (like target selection)
                for msg in self.all_messages:
                    try:
                        await msg.delete()
                    except (discord.NotFound, discord.HTTPException):
                        pass
            except (discord.NotFound, discord.HTTPException):
                pass
            
            # Handle random scenario if crime type is random
            if self.crime_type == "random":
                self.scenario = get_random_scenario()
                self.crime_data = self.crime_data.copy()  # Create a copy to modify
                self.crime_data.update({
                    "min_reward": self.scenario["min_reward"],
                    "max_reward": self.scenario["max_reward"],
                    "success_rate": self.scenario["success_rate"],
                    "jail_time": self.scenario["jail_time"],
                    "risk": self.scenario["risk"],
                    "fine_multiplier": self.scenario["fine_multiplier"]
                })
            
            # Get attempt message based on crime type
            if self.crime_type == "random":
                attempt_msg = _(self.scenario["attempt_text"]).format(
                    user=self.interaction.user.mention
                )
            elif self.crime_type == "pickpocket":
                attempt_msg = _("🧤 {user} begins to slip their hand towards {target}'s pocket...").format(
                    user=self.interaction.user.mention,
                    target=self.target.display_name
                )
            elif self.crime_type == "mugging":
                attempt_msg = _("🔪 {user} lurks in the shadows, waiting for {target}...").format(
                    user=self.interaction.user.mention,
                    target=self.target.display_name
                )
            elif self.crime_type == "rob_store":
                attempt_msg = _("🏪 {user} pulls out their weapon and approaches the store...").format(
                    user=self.interaction.user.mention
                )
            else:  # bank heist
                attempt_msg = _("🏛 {user} begins their elaborate plan to breach the bank vault...").format(
                    user=self.interaction.user.mention
                )
            
            # Create and send attempt message with bail out button
            attempt_view = CrimeAttemptView(self.cog, interaction, self.crime_type)
            msg = await interaction.channel.send(attempt_msg, view=attempt_view)
            attempt_view.message = msg
            self.all_messages.append(msg)

            # Short pause after attempt message
            await asyncio.sleep(2)

            # Check if user bailed out
            if attempt_view.bailed:
                return

            # Initialize modifiers
            success_chance = self.crime_data["success_rate"]
            jail_time = self.crime_data["jail_time"]
            reward_multiplier = 1.0
            total_credit_changes = 0  # Track direct credit changes

            # Get and process events if this is not a random crime
            if self.crime_type != "random":
                events = get_crime_event(self.crime_type)
                
                # Process each event
                for event in events:
                    # Check for bail out after each event
                    if attempt_view.bailed:
                        return
                        
                    # Send event message with delay
                    event_text = event["text"]
                    format_args = {}
                    
                    # Add credit amounts if present
                    if "credits_bonus" in event:
                        format_args["credits_bonus"] = str(event["credits_bonus"])
                    elif "credits_penalty" in event:
                        format_args["credits_penalty"] = str(event["credits_penalty"])
                    
                    # Format the message with all arguments at once
                    msg = await interaction.channel.send(await format_text(event_text, interaction, **format_args))
                    self.all_messages.append(msg)
                    await asyncio.sleep(3.5)  # Increased delay between events (was 2s)

                    # Apply event modifiers
                    if "chance_bonus" in event:
                        success_chance = min(1.0, success_chance + event["chance_bonus"])
                    elif "chance_penalty" in event:
                        success_chance = max(0.05, success_chance - event["chance_penalty"])
                    
                    if "reward_multiplier" in event:
                        reward_multiplier *= event["reward_multiplier"]
                    
                    if "jail_multiplier" in event:
                        jail_time = int(jail_time * event["jail_multiplier"])
                        
                    # Handle direct credit changes
                    if "credits_bonus" in event:
                        bonus = event["credits_bonus"]
                        await bank.deposit_credits(interaction.user, bonus)
                        total_credit_changes += bonus
                    elif "credits_penalty" in event:
                        penalty = event["credits_penalty"]
                        try:
                            await bank.withdraw_credits(interaction.user, penalty)
                            total_credit_changes -= penalty
                        except ValueError:
                            # If user doesn't have enough credits, take what they have
                            current_balance = await bank.get_balance(interaction.user)
                            if current_balance > 0:
                                await bank.withdraw_credits(interaction.user, current_balance)
                                total_credit_changes -= current_balance
                            
            # Add suspense delay based on risk level
            if self.crime_data["risk"] == "high":
                await asyncio.sleep(6)  # More suspense for high-risk crimes (was 6s)
            elif self.crime_data["risk"] == "medium":
                await asyncio.sleep(5)  # Medium delay for medium-risk (was 5s)
            else:
                await asyncio.sleep(4)  # Quick result for low-risk (was 4s)

            # Final bail out check before result
            if attempt_view.bailed:
                return

            # Clean up attempt view
            attempt_view.stop()
            
            # Roll for success
            success = random.random() < success_chance
            
            if success:
                # Handle success
                if self.target:
                    # For targeted crimes
                    self.crime_data["crime_type"] = self.crime_type  # Add crime type to data
                    try:
                        # Calculate amount to steal first
                        amount = await calculate_stolen_amount(self.target, self.crime_data, settings)
                        
                        # Apply reward multiplier from events
                        amount = int(amount * reward_multiplier)
                        
                        # Check target's balance and perform transfer atomically
                        try:
                            target_balance = await bank.get_balance(self.target)
                            min_required = max(settings.get("min_steal_balance", 100), self.crime_data["min_reward"])
                            
                            if target_balance < min_required:
                                msg = await interaction.channel.send(
                                    _("Your target doesn't have enough {currency} to steal from! (Minimum: {min:,})").format(
                                        currency=await bank.get_currency_name(interaction.guild),
                                        min=min_required
                                    )
                                )
                                self.all_messages.append(msg)
                                return
                                
                            # Try to perform the transfers
                            await bank.withdraw_credits(self.target, amount)
                            await bank.deposit_credits(interaction.user, amount)
                            
                            # Update stats and last target
                            async with self.cog.config.member(interaction.user).all() as user_data:
                                user_data["total_stolen_from"] += amount
                                user_data["total_credits_earned"] += amount
                                user_data["last_target"] = self.target.id
                                user_data["total_successful_crimes"] += 1
                                if amount > user_data.get("largest_heist", 0):
                                    user_data["largest_heist"] = amount
                                    
                            async with self.cog.config.member(self.target).all() as target_data:
                                target_data["total_stolen_by"] += amount
                                
                            # Send success message
                            msg = await interaction.channel.send(
                                embed=await self.format_crime_message(
                                    True,
                                    target=self.target,
                                    reward=amount,
                                    rate=int(success_chance * 100),
                                    settings=settings,
                                    credit_changes=total_credit_changes
                                )
                            )
                            self.all_messages.append(msg)
                            for item in attempt_view.children:
                                item.disabled = True
                            await attempt_view.message.edit(view=attempt_view)
                            self.stop()  # Stop the view after success
                            
                        except discord.HTTPException as e:
                            await interaction.channel.send(
                                _("Failed to steal from target - they may not have enough {currency}. Error: {error}").format(
                                    currency=await bank.get_currency_name(interaction.guild),
                                    error=str(e)
                                )
                            )
                            self.all_messages.append(msg)
                            return
                            
                    except Exception as e:
                        await interaction.channel.send(
                            _("An error occurred while processing the crime. Please try again. Error: {error}").format(
                                error=str(e)
                            )
                        )
                        self.all_messages.append(msg)
                        return

                else:
                    try:
                        # For non-targeted crimes
                        amount = random.randint(self.crime_data["min_reward"], self.crime_data["max_reward"])
                        # Apply reward multiplier from events
                        amount = int(amount * reward_multiplier)
                        await bank.deposit_credits(interaction.user, amount)
                        
                        # Send success message
                        msg = await interaction.channel.send(
                            embed=await self.format_crime_message(
                                True,
                                reward=amount,
                                rate=int(success_chance * 100),
                                settings=settings,
                                credit_changes=total_credit_changes
                            )
                        )
                        self.all_messages.append(msg)
                        for item in attempt_view.children:
                            item.disabled = True
                        await attempt_view.message.edit(view=attempt_view)
                        self.stop()  # Stop the view after success
                        
                        # Update stats
                        async with self.cog.config.member(interaction.user).all() as user_data:
                            user_data["total_credits_earned"] += amount
                            user_data["total_successful_crimes"] += 1
                            if amount > user_data.get("largest_heist", 0):
                                user_data["largest_heist"] = amount
                                
                    except Exception as e:
                        await interaction.channel.send(
                            _("An error occurred while processing your crime. Please try again. Error: {error}").format(
                                error=str(e)
                            )
                        )
                        self.all_messages.append(msg)
                        return
            else:
                # Crime failed, processing penalties
                fine_amount = int(self.crime_data["max_reward"] * self.crime_data["fine_multiplier"])
                actual_fine = 0  # Track how much was actually paid
                
                # Apply fine if user can afford it
                try:
                    user_balance = await bank.get_balance(interaction.user)
                    if user_balance >= fine_amount:
                        await bank.withdraw_credits(interaction.user, fine_amount)
                        actual_fine = fine_amount
                        async with self.cog.config.member(interaction.user).all() as user_data:
                            user_data["total_fines_paid"] += fine_amount
                    else:
                        # Take all their money and double jail time
                        if user_balance > 0:  # Only take money if they have any
                            await bank.withdraw_credits(interaction.user, user_balance)
                            actual_fine = user_balance
                            async with self.cog.config.member(interaction.user).all() as user_data:
                                user_data["total_fines_paid"] += user_balance

                        # Double the jail time
                        jail_time *= 2
                        await interaction.channel.send(
                            _("You cannot afford the fine of {fine:,} {currency}. All your money has been confiscated and your jail time has been doubled!").format(
                                fine=fine_amount,
                                currency=await bank.get_currency_name(interaction.guild)
                            )
                        )

                except Exception as e:
                    await interaction.channel.send(
                        _("Failed to apply fine. Error: {error}").format(
                            error=str(e)
                        )
                    )
                    self.all_messages.append(msg)
                    return
                
                # Send failure message
                msg = await interaction.channel.send(
                    embed=await self.format_crime_message(
                        False,
                        fine=actual_fine,
                        jail_time=jail_time,
                        rate=int(success_chance * 100),
                        settings=settings,
                        credit_changes=total_credit_changes
                    )
                )
                self.all_messages.append(msg)
                for item in attempt_view.children:
                    item.disabled = True
                await attempt_view.message.edit(view=attempt_view)
                self.stop()  # Stop the view after failure
                
                # Update stats
                async with self.cog.config.member(interaction.user).all() as user_data:
                    user_data["total_failed_crimes"] += 1
                
                # Send to jail
                await self.cog.send_to_jail(interaction.user, jail_time)
                
            # Set cooldown
            await self.cog.set_action_cooldown(interaction.user, self.crime_type)
            
        except Exception as e:
            await interaction.channel.send(
                _("An error occurred while processing your crime. Please try again. Error: {error}").format(
                    error=str(e)
                )
            )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the crime attempt"""
        if interaction.user.bot:
            return
            
        try:
            # Delete only the confirmation message
            try:
                await self.message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            
            # Send cancellation message
            msg = await interaction.channel.send(_("Crime cancelled."))
            self.stop()
        except Exception as e:
            await interaction.channel.send(
                _("An error occurred while cancelling the crime. Error: {error}").format(
                    error=str(e)
                )
            )
            self.stop()
            
class CrimeAttemptView(discord.ui.View):
    """View for the crime attempt message with Bail Out button."""
    
    def __init__(self, cog, interaction: discord.Interaction, crime_type: str):
        super().__init__(timeout=30)
        self.cog = cog
        self.interaction = interaction
        self.crime_type = crime_type
        self.message = None
        self.bailed = False
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original user to use the view."""
        return interaction.user.id == self.interaction.user.id
        
    @discord.ui.button(label="Bail Out!", style=discord.ButtonStyle.danger, emoji="🏃")
    async def bail_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle bailing out of a crime attempt"""
        if interaction.user.bot:
            return
            
        try:
            await interaction.response.defer()
            
            # Deduct bail out cost
            currency = await bank.get_currency_name(interaction.guild)
            try:
                await bank.withdraw_credits(interaction.user, 100)
            except ValueError:
                await interaction.followup.send(
                    _("You don't have enough {currency} to bail out! (Cost: 100)").format(
                        currency=currency
                    ),
                    ephemeral=True
                )
                return

            # Set cooldown
            await self.cog.set_action_cooldown(interaction.user, self.crime_type)

            # Disable the button
            button.disabled = True
            await self.message.edit(view=self)

            # Send bail out message
            embed = discord.Embed(
                title="🏃 Bailed Out!",
                description=f"{interaction.user.mention} chickened out and bailed on the {self.crime_type.replace('_', ' ')}!",
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="Cost",
                value=f"100 {currency}",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
            # Set bailed flag
            self.bailed = True
            
            # Stop the view
            self.stop()
            
        except Exception as e:
            await interaction.followup.send(
                _("An error occurred while bailing out. Error: {error}").format(
                    error=str(e)
                ),
                ephemeral=True
            )
            self.stop()

    async def on_timeout(self) -> None:
        """Handle view timeout"""
        if self.bailed:
            # If already bailed out, don't try to modify the message
            return
            
        try:
            # Disable the button
            for item in self.children:
                item.disabled = True
                
            # Try to update the message if it still exists
            if self.message:
                try:
                    await self.message.edit(view=self)
                except (discord.NotFound, discord.HTTPException):
                    # Message was deleted or became invalid, just ignore
                    pass
        except Exception as e:
            # Log any other unexpected errors but don't try to send them
            # since the channel/message might not be available
            pass
            
class BailView(discord.ui.View):
    """View for paying bail"""
    def __init__(self, cog, ctx: commands.Context, bail_amount: int, jail_time: int):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
        self.bail_amount = bail_amount
        self.jail_time = jail_time
        self.message = None  # Will store the initial bail prompt message
        self.all_messages = []  # Track all messages
        
    def format_bail_embed(self, title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
        """Format a bail-related embed with consistent styling."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Requested by {self.ctx.author.display_name}", icon_url=self.ctx.author.display_avatar.url)
        return embed
        
    async def cleanup_messages(self):
        """Clean up all messages sent during the bail process"""
        try:
            # Always add the initial bail prompt message to cleanup list
            if self.message:
                self.all_messages.append(self.message)
                
            for msg in self.all_messages:
                try:
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
        except Exception as e:
            error_embed = self.format_bail_embed(
                "⚠️ Error",
                f"An error occurred while cleaning up messages: {str(e)}",
                discord.Color.red()
            )
            await self.message.channel.send(embed=error_embed)
            
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the author that invoked the command to use the interaction"""
        return interaction.user.id == self.ctx.author.id
        
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle any errors that occur during button interactions"""
        error_embed = self.format_bail_embed(
            "⚠️ Error",
            f"An error occurred. Please try again: {str(error)}",
            discord.Color.red()
        )
        msg = await interaction.channel.send(embed=error_embed)
        self.all_messages.append(msg)
        await self.cleanup_messages()
        self.stop()
        
    @discord.ui.button(label="Pay Bail", style=discord.ButtonStyle.success, emoji="💸")
    async def pay_bail(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pay bail and get out of jail"""
        if interaction.user.bot:
            return
            
        try:
            # Get current balance and currency name
            current_balance = await bank.get_balance(interaction.user)
            currency_name = await bank.get_currency_name(interaction.guild)
            
            # Check if user has enough credits
            if not await bank.can_spend(interaction.user, self.bail_amount):
                insufficient_embed = self.format_bail_embed(
                    "💵 Insufficient Funds",
                    f"You don't have enough {currency_name} to pay bail!\n\n"
                    f"**Required:** {self.bail_amount:,} {currency_name}\n"
                    f"**Current Balance:** {current_balance:,} {currency_name}",
                    discord.Color.red()
                )
                msg = await interaction.channel.send(embed=insufficient_embed)
                self.all_messages.append(msg)
                return
                
            # Pay bail and remove from jail
            await bank.withdraw_credits(interaction.user, self.bail_amount)
            
            # Get new balance
            new_balance = await bank.get_balance(interaction.user)
            
            # Update jail status and stats
            async with self.cog.config.member(interaction.user).all() as user_data:
                user_data["jail_until"] = 0
                user_data["total_bail_paid"] = user_data.get("total_bail_paid", 0) + self.bail_amount
            
            # Clean up the bail prompt first
            await self.cleanup_messages()
            
            # Send success message (this one stays)
            success_embed = self.format_bail_embed(
                "🔓 Bail Paid Successfully!",
                f"You have been released from jail.\n\n"
                f"**Bail Cost:** {self.bail_amount:,} {currency_name}\n"
                f"**Previous Balance:** {current_balance:,} {currency_name}\n"
                f"**New Balance:** {new_balance:,} {currency_name}",
                discord.Color.green()
            )
            await interaction.channel.send(embed=success_embed)
            self.stop()
            
        except Exception as e:
            error_embed = self.format_bail_embed(
                "⚠️ Error",
                f"An error occurred while paying bail: {str(e)}",
                discord.Color.red()
            )
            msg = await interaction.channel.send(embed=error_embed)
            self.all_messages.append(msg)
            await self.cleanup_messages()
            self.stop()
            
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel bail payment"""
        if interaction.user.bot:
            return
            
        try:
            minutes = self.jail_time // 60
            seconds = self.jail_time % 60
            
            cancel_embed = self.format_bail_embed(
                "❌ Bail Cancelled",
                f"You have chosen to serve your time.\n\n"
                f"**Time Remaining:** {minutes}m {seconds}s",
                discord.Color.orange()
            )
            msg = await interaction.channel.send(embed=cancel_embed)
            self.all_messages.append(msg)
            await self.cleanup_messages()
            self.stop()
        except Exception as e:
            error_embed = self.format_bail_embed(
                "⚠️ Error",
                f"An error occurred while cancelling bail: {str(e)}",
                discord.Color.red()
            )
            await interaction.channel.send(embed=error_embed)
            
    async def on_timeout(self):
        """Handle view timeout"""
        try:
            for item in self.children:
                item.disabled = True
            if self.message:
                await self.message.edit(view=self)
                timeout_embed = self.format_bail_embed(
                    "⏰ Time's Up",
                    "Bail payment timed out.",
                    discord.Color.greyple()
                )
                msg = await self.message.channel.send(embed=timeout_embed)
                self.all_messages.append(msg)
                await self.cleanup_messages()
        except Exception:
            # Silently handle any other errors since the channel might not be available
            pass
        finally:
            self.stop()

class TargetModal(discord.ui.Modal):
    """Modal for entering target information"""
    def __init__(self, view):
        super().__init__(title="Select Target")
        self.view = view
        
        self.target_input = discord.ui.TextInput(
            label="Target User",
            placeholder="Enter username, nickname, or ID",
            required=True,
            min_length=1,
            max_length=100
        )
        self.add_item(self.target_input)
        
    async def on_submit(self, interaction: discord.Interaction):
        """Handle target selection submission"""
        try:
            # Try to find the target member
            target = None
            input_value = self.target_input.value.lower()
            
            # Search through guild members
            for member in interaction.guild.members:
                if (input_value in member.name.lower() or 
                    input_value in member.display_name.lower() or 
                    input_value == str(member.id)):
                    target = member
                    break
                    
            if not target:
                msg = await interaction.channel.send(
                    _("Could not find a member named '{name}'. Please check the spelling and try again.").format(
                        name=self.target_input.value
                    )
                )
                self.view.all_messages.append(msg)
                return
                
            # Check if target is valid
            settings = await self.view.cog.config.guild(interaction.guild).global_settings()
            can_target, reason = await can_target_for_crime(self.view.cog, interaction, target, self.view.crime_data, settings)
            
            if not can_target:
                msg = await interaction.channel.send(reason)
                self.view.all_messages.append(msg)
                return
                
            # Check target's balance before proceeding
            try:
                target_balance = await bank.get_balance(target)
                min_required = max(settings.get("min_steal_balance", 100), self.view.crime_data["min_reward"])
                
                if target_balance < min_required:
                    msg = await interaction.channel.send(
                        _("This target doesn't have enough {currency} to steal from! (Minimum: {min:,})").format(
                            currency=await bank.get_currency_name(interaction.guild),
                            min=min_required
                        )
                    )
                    self.view.all_messages.append(msg)
                    return
            except Exception as e:
                await interaction.channel.send(
                    _("An error occurred while checking your target's balance. Please try again. Error: {error}").format(
                        error=str(e)
                    )
                )
                self.view.all_messages.append(msg)
                return
                
            # Create crime view with selected target
            crime_view = CrimeView(self.view.cog, interaction, self.view.crime_type, self.view.crime_data, target=target)
            
            embed = discord.Embed(
                title=f"{self.view.crime_data.get('emoji', '🎯')} Target Selected",
                description=f"Ready to attempt {self.view.crime_type.replace('_', ' ')} against {target.display_name}?",
                color=discord.Color.red()
            )
            embed.add_field(
                name="📊 Success Rate",
                value=f"{int(self.view.crime_data['success_rate'] * 100)}%",
                inline=True
            )
            embed.add_field(
                name="💸 Potential Fine",
                value=f"{int(self.view.crime_data['max_reward'] * self.view.crime_data['fine_multiplier']):,} {await bank.get_currency_name(interaction.guild)}",
                inline=True
            )
            
            message = await interaction.channel.send(
                embed=embed,
                view=crime_view
            )
            crime_view.message = message
            crime_view.all_messages = self.view.all_messages + [message]  # Pass message list to crime view
            
            # Stop the target selection view
            self.view.stop()
            
        except Exception as e:
            await interaction.channel.send(
                _("An error occurred while selecting the target. Please try again. Error: {error}").format(
                    error=str(e)
                )
            )
            self.view.all_messages.append(msg)

class TargetSelectionView(discord.ui.View):
    """View for selecting a target"""
    def __init__(self, cog, interaction: discord.Interaction, crime_type: str, crime_data: dict):
        super().__init__(timeout=30)
        self.cog = cog
        self.interaction = interaction
        self.crime_type = crime_type
        self.crime_data = crime_data
        self.target = None
        self.message = None
        self.all_messages = []  # Track all messages
        
    async def cleanup_messages(self):
        """Clean up all messages sent during the crime process"""
        try:
            for msg in self.all_messages:
                try:
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
        except Exception as e:
            await self.message.channel.send(
                _("An error occurred while cleaning up messages. Error: {error}").format(
                    error=str(e)
                )
            )
            
    async def get_random_target(self) -> Optional[discord.Member]:
        """Get a random valid target from the guild."""
        try:
            # Get settings
            settings = await self.cog.config.guild(self.interaction.guild).global_settings()
            min_required = max(settings.get("min_steal_balance", 100), self.crime_data["min_reward"])
            
            # Get list of valid targets
            valid_targets = []
            for member in self.interaction.guild.members:
                # Skip if can't target
                can_target, _ = await can_target_for_crime(self.cog, self.interaction, member, self.crime_data, settings)
                if not can_target:
                    continue
                    
                try:
                    # Check if member has enough credits
                    balance = await bank.get_balance(member)
                    if balance >= min_required:
                        valid_targets.append(member)
                except Exception as e:
                    await self.message.channel.send(
                        _("An error occurred while checking balance for {member}. Error: {error}").format(
                            member=member,
                            error=str(e)
                        )
                    )
                    continue
            
            if not valid_targets:
                await self.interaction.channel.send(
                    _("No valid targets found! Everyone is either broke, a bot, or immune to crime.")
                )
                return None
                
            # Return random target from valid list
            return random.choice(valid_targets)
            
        except Exception as e:
            await self.message.channel.send(
                _("An error occurred while finding a random target. Error: {error}").format(
                    error=str(e)
                )
            )
            return None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the author that invoked the command to use the interaction"""
        return interaction.user == self.interaction.user
        
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle any errors that occur during button interactions"""
        await interaction.channel.send(
            _("An error occurred. Please try again. Error: {error}").format(
                error=str(error)
            )
        )
        self.all_messages.append(msg)
        await self.cleanup_messages()
        self.stop()
        
    @discord.ui.button(label="Random Target", style=discord.ButtonStyle.primary)
    async def random_target(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select a random target"""
        if interaction.user.bot:
            return
            
        try:
            await interaction.response.defer()
            
            target = await self.get_random_target()
            if target:
                # Create crime view with selected target
                crime_view = CrimeView(self.cog, interaction, self.crime_type, self.crime_data, target=target)
                
                embed = discord.Embed(
                    title=f"{self.crime_data.get('emoji', '🎯')} Target Selected",
                    description=f"Ready to attempt {self.crime_type.replace('_', ' ')} against {target.display_name}?",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="📊 Success Rate",
                    value=f"{int(self.crime_data['success_rate'] * 100)}%",
                    inline=True
                )
                embed.add_field(
                    name="💸 Potential Fine",
                    value=f"{int(self.crime_data['max_reward'] * self.crime_data['fine_multiplier']):,} {await bank.get_currency_name(interaction.guild)}",
                    inline=True
                )
                
                message = await interaction.channel.send(
                    embed=embed,
                    view=crime_view
                )
                crime_view.message = message
                crime_view.all_messages = self.all_messages + [message]  # Pass message list to crime view
                self.stop()
            else:
                settings = await self.cog.config.guild(interaction.guild).global_settings()
                await interaction.channel.send(
                    _("No valid targets found. A valid target must:\n"
                      "• Have at least {min_balance:,} {currency}\n"
                      "• Not be your last target\n"
                      "• Not be in jail\n"
                      "Try again later or choose a specific target.").format(
                        min_balance=settings.get("min_steal_balance", 100),
                        currency=await bank.get_currency_name(interaction.guild)
                    )
                )
                self.all_messages.append(msg)
                await self.cleanup_messages()
        except Exception as e:
            await interaction.channel.send(
                _("An error occurred while selecting a target. Please try again. Error: {error}").format(
                    error=str(e)
                )
            )
            self.all_messages.append(msg)
            await self.cleanup_messages()
        
    @discord.ui.button(label="Select Target", style=discord.ButtonStyle.success)
    async def select_target(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal to select specific target"""
        if interaction.user.bot:
            return
            
        modal = TargetModal(self)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel target selection"""
        if interaction.user.bot:
            return
            
        await interaction.response.defer()
        msg = await interaction.channel.send(_("Crime cancelled."))
        self.all_messages.append(msg)
        await self.cleanup_messages()
        self.target = None
        self.stop()
        
    async def on_timeout(self):
        """Handle view timeout"""
        try:
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Try to update the message if it still exists
            if self.message:
                try:
                    await self.message.edit(view=self)
                    try:
                        msg = await self.message.channel.send(_("Target selection timed out."))
                        self.all_messages.append(msg)
                        await self.cleanup_messages()
                    except discord.HTTPException:
                        pass
                except (discord.NotFound, discord.HTTPException):
                    pass
        except Exception:
            # Silently handle any other errors since the channel might not be available
            pass
        finally:
            self.stop()
            
async def can_target_for_crime(cog, interaction: discord.Interaction, target: discord.Member, crime_data: dict, settings: dict) -> Tuple[bool, str]:
    """Check if a user can be targeted for a crime.
    
    Args:
        cog: The crime cog instance
        interaction: The discord interaction
        target: The member to check if can be targeted
        crime_data: The crime data containing requirements
        settings: Global settings containing minimum balance requirements
    
    Returns:
        tuple of (can_target, reason)
    """
    # First do basic checks using the utility function
    # Add min_balance_required flag for crime actions
    crime_data = {**crime_data, "min_balance_required": True}
    can_target, reason = await can_target_user(interaction, target, crime_data, settings)
    if not can_target:
        return False, reason
        
    # Check if target is jailed
    if await cog.is_jailed(target):
        return False, _("That user is in jail!")
        
    # Check if target was last victim
    last_target = await cog.config.member(interaction.user).last_target()
    if last_target is not None and last_target == target.id:
        return False, _("You can't target your last victim!")
        
    return True, ""
