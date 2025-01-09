"""Utility functions for the city cog."""

import discord
from redbot.core import bank, commands
from datetime import datetime, timezone
import time
import random
from typing import Optional, Tuple, Union, List, Dict

def format_cooldown_time(seconds: int, include_emoji: bool = True) -> str:
    """Format cooldown time into a human readable string.
    
    Args:
        seconds: Number of seconds to format
        include_emoji: Whether to include the ⏳ emoji
        
    Returns:
        Formatted string like "2h 30m" or "5m 30s"
    """
    if seconds <= 0:
        return "✅" if include_emoji else "Ready"
        
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        time_str = f"{hours}h {minutes}m"
    elif minutes > 0:
        time_str = f"{minutes}m {seconds}s"
    else:
        time_str = f"{seconds}s"
        
    return f"⏳ {time_str}" if include_emoji else time_str

async def can_target_user(interaction_or_ctx: Union[discord.Interaction, commands.Context], target: discord.Member, action_data: dict, settings: dict) -> Tuple[bool, str]:
    """Base targeting checks for any action.
    
    Args:
        interaction_or_ctx: Either a discord.Interaction or commands.Context
        target: The member to check if can be targeted
        action_data: The action data containing requirements
        settings: Global settings containing minimum balance requirements
    
    Returns:
        tuple of (can_target, reason)
    """
    # Get the author from either interaction or context
    if isinstance(interaction_or_ctx, discord.Interaction):
        author = interaction_or_ctx.user
    else:
        author = interaction_or_ctx.author
    
    # Can't target self
    if target.id == author.id:
        return False, "You can't target yourself!"
        
    # Can't target bots
    if target.bot:
        return False, "You can't target bots!"
        
    try:
        # Check target's balance if minimum is specified
        if "min_balance_required" in action_data:
            target_balance = await bank.get_balance(target)
            min_balance = settings.get("min_steal_balance", 100)
            
            if target_balance < min_balance:
                return False, f"Target must have at least {min_balance:,} credits!"
            
            # For actions with steal percentages, check if target has enough based on percentage
            if "steal_percentage" in action_data:
                steal_percentage = action_data["steal_percentage"]
                max_steal = settings.get("max_steal_amount", 1000)
                
                # Calculate potential steal amount
                potential_steal = min(int(target_balance * steal_percentage), max_steal)
                
                if potential_steal < action_data.get("min_reward", 0):
                    return False, f"Target doesn't have enough credits! (Needs at least {int(action_data['min_reward'] / steal_percentage):,} credits)"
                    
    except Exception as e:
        return False, f"Error checking target's balance: {str(e)}"
        
    return True, ""

async def calculate_stolen_amount(target: discord.Member, crime_data: dict, settings: dict) -> int:
    """Calculate how much to steal from the target based on settings.
    
    Args:
        target: The member being stolen from
        crime_data: The crime data containing requirements
        settings: Global settings containing maximum steal amount
        
    Returns:
        Amount to steal, or 0 if error
    """
    try:
        # Get target's balance
        target_balance = await bank.get_balance(target)
        
        # For crimes with steal percentages, calculate based on balance
        if "min_steal_percentage" in crime_data and "max_steal_percentage" in crime_data:
            # Get random percentage between min and max
            steal_percentage = random.uniform(
                crime_data["min_steal_percentage"],
                crime_data["max_steal_percentage"]
            )
            
            # Calculate amount to steal
            amount = int(target_balance * steal_percentage)
            
            # Cap at max_steal_amount from settings
            max_steal = settings.get("max_steal_amount", 1000)
            amount = min(amount, max_steal)
            
            # Cap at crime's max_reward
            amount = min(amount, crime_data["max_reward"])
            
            # Ensure at least min_reward if target has enough balance
            if amount < crime_data["min_reward"] and target_balance >= (crime_data["min_reward"] / crime_data["min_steal_percentage"]):
                amount = crime_data["min_reward"]
                
            return amount
            
        # For other crimes, use normal random range
        return random.randint(crime_data["min_reward"], crime_data["max_reward"])
            
    except Exception:
        return 0

def get_crime_emoji(crime_type: str) -> str:
    """Get the appropriate emoji for a crime type.
    
    Args:
        crime_type: The type of crime (pickpocket, mugging, rob_store, bank_heist, random)
        
    Returns:
        The corresponding emoji for the crime type:
        • 🧤 for pickpocket
        • 🔪 for mugging
        • 🏪 for store robbery
        • 🏛 for bank heist
        • 🎲 for random crimes
    """
    emojis = {
        "pickpocket": "🧤",
        "mugging": "🔪",
        "rob_store": "🏪",
        "bank_heist": "🏛",
        "random": "🎲"
    }
    return emojis.get(crime_type, "🦹")  # Default to generic criminal emoji

def get_risk_emoji(risk_level: str) -> str:
    """Get the emoji for a risk level.
    
    Args:
        risk_level: The risk level (low, medium, high)
        
    Returns:
        Emoji representing the risk level
    """
    emoji_map = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🔴"
    }
    return emoji_map.get(risk_level, "🤔")

def format_crime_description(crime_type: str, data: dict, cooldown_status: str) -> str:
    """Format a crime's description for display in embeds.
    
    Args:
        crime_type: The type of crime
        data: Dictionary containing crime data (success_rate, min_reward, max_reward, etc.)
        cooldown_status: Formatted cooldown status string
        
    Returns:
        A formatted description string containing:
        • Success rate percentage
        • Reward range (percentage based for pickpocket/mugging)
        • Risk level indicator
        • Cooldown status
        • Whether it requires a target
    """
    # Get risk emoji
    risk_emoji = "???" if crime_type == "random" else "🟢" if data["risk"] == "low" else "🟡" if data["risk"] == "medium" else "🔴"
    
    # Format description based on crime type
    if crime_type == "random":
        description = [
            "**Success Rate:** ???",
            "**Reward:** ???",
            f"**Risk Level:** {risk_emoji}",
            f"**Cooldown:** {cooldown_status}"
        ]
    elif crime_type == "pickpocket":
        description = [
            f"**Success Rate:** {int(data['success_rate'] * 100)}%",
            "**Reward:** 1-10% of target's balance (max 500)",
            f"**Risk Level:** {risk_emoji}",
            f"**Cooldown:** {cooldown_status}",
            "**Target Required:** Yes"
        ]
    elif crime_type == "mugging":
        description = [
            f"**Success Rate:** {int(data['success_rate'] * 100)}%",
            "**Reward:** 15-25% of target's balance (max 1500)",
            f"**Risk Level:** {risk_emoji}",
            f"**Cooldown:** {cooldown_status}",
            "**Target Required:** Yes"
        ]
    else:
        description = [
            f"**Success Rate:** {int(data['success_rate'] * 100)}%",
            f"**Reward:** {data['min_reward']:,} - {data['max_reward']:,}",
            f"**Risk Level:** {risk_emoji}",
            f"**Cooldown:** {cooldown_status}"
        ]
            
    return "\n".join(description)

def calculate_streak_bonus(streak: int) -> float:
    """Calculate reward multiplier based on current streak.
    
    The bonus increases with streak but has diminishing returns:
    Streak 1: +5% (1.05x)
    Streak 2: +10% (1.10x)
    Streak 3: +15% (1.15x)
    Streak 4: +20% (1.20x)
    Streak 5+: +25% (1.25x) max
    """
    if streak <= 0:
        return 1.0
    
    # Calculate bonus with diminishing returns
    bonus = min(0.25, streak * 0.05)  # Cap at 25% bonus
    return 1.0 + bonus

async def update_streak(config, member: discord.Member, success: bool) -> tuple[int, float]:
    """Update a member's crime streak and return new streak and multiplier.
    
    Args:
        config: The config instance to use for data storage
        member (discord.Member): The member to update
        success (bool): Whether the crime was successful
        
    Returns:
        tuple[int, float]: The new streak count and reward multiplier
    """
    async with config.member(member).all() as member_data:
        current_time = int(time.time())
        last_crime = member_data.get("last_crime_time", 0)
        
        # Reset streak if it's been more than 24 hours since last crime
        if current_time - last_crime > 86400:  # 24 hours in seconds
            member_data["current_streak"] = 0
        
        if success:
            # Increment streak on success
            member_data["current_streak"] += 1
            # Update highest streak if current is higher
            if member_data["current_streak"] > member_data.get("highest_streak", 0):
                member_data["highest_streak"] = member_data["current_streak"]
        else:
            # Reset streak on failure
            member_data["current_streak"] = 0
        
        # Update last crime time
        member_data["last_crime_time"] = current_time
        
        # Calculate new multiplier
        new_multiplier = calculate_streak_bonus(member_data["current_streak"])
        member_data["streak_multiplier"] = new_multiplier
        
        return member_data["current_streak"], new_multiplier

def format_streak_text(streak: int, multiplier: float) -> str:
    """Format streak information for display in embeds.
    
    Args:
        streak (int): Current streak count
        multiplier (float): Current reward multiplier
        
    Returns:
        str: Formatted streak text
    """
    if streak <= 0:
        return "No active streak"
        
    bonus_percent = (multiplier - 1.0) * 100
    return f"🔥 {streak} streak (+{bonus_percent:.0f}%)"
