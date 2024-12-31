"""Utility functions for the city cog."""

import discord
from redbot.core import bank
from datetime import datetime, timezone
import time
import random
from typing import Optional, Tuple

async def get_remaining_cooldown(config, member: discord.Member, action_type: str, action_data: dict) -> int:
    """Get the remaining cooldown time for an action in seconds."""
    current_time = int(time.time())
    last_actions = await config.member(member).last_actions()
    
    # Get the last time this action was attempted
    last_attempt = last_actions.get(action_type, 0)
    if not last_attempt:
        return 0
        
    # Get cooldown duration
    cooldown = action_data["cooldown"]
    
    # Calculate remaining time
    elapsed = current_time - last_attempt
    remaining = max(0, cooldown - elapsed)
    
    return remaining

async def set_action_cooldown(config, member: discord.Member, action_type: str):
    """Set cooldown for an action type"""
    current_time = int(time.time())
    async with config.member(member).last_actions() as last_actions:
        last_actions[action_type] = current_time

def format_cooldown_time(seconds: int, include_emoji: bool = True) -> str:
    """Format cooldown time into a human readable string.
    
    Args:
        seconds: Number of seconds to format
        include_emoji: Whether to include the ⏳ emoji
        
    Returns:
        Formatted string like "2h 30m" or "5m 30s"
    """
    if seconds <= 0:
        return "✅ Ready" if include_emoji else "Ready"
        
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        time_str = f"{hours}h {minutes}m"
    else:
        time_str = f"{minutes}m {seconds}s"
        
    return f"⏳ {time_str}" if include_emoji else time_str

async def can_target_user(interaction_or_ctx, target: discord.Member, action_data: dict, settings: dict) -> Tuple[bool, str]:
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

async def calculate_stolen_amount(target: discord.Member, crime_data: dict, settings: dict):
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
    """Get the emoji for a crime type.
    
    Args:
        crime_type: The type of crime
        
    Returns:
        Emoji representing the crime type
    """
    emoji_map = {
        "pickpocket": "🧤",
        "mugging": "🔪", 
        "rob_store": "🏪",
        "bank_heist": "🏛",
        "random": "🎲"
    }
    return emoji_map.get(crime_type, "🤔")

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

def format_crime_description(crime_type: str, data: dict, status: str) -> str:
    """Format the description for a crime type.
    
    Args:
        crime_type: The type of crime
        data: Crime data dictionary
        status: Current status string
        
    Returns:
        Formatted description string
    """
    risk_emoji = get_risk_emoji(data["risk"])
    
    if crime_type == "random":
        description = (
            f"{risk_emoji} **Risk Level:** ???\n"
            f"**Reward:** ???\n"
            f"**Success Rate:** ???\n"
            f"**Jail Time:** ???\n"
            f"**Status:** {status}"
        )
    elif crime_type == "pickpocket":
        description = (
            f"{risk_emoji} **Risk Level:** {data['risk'].title()}\n"
            f"**Reward:** 1-10% of target's balance (max 500)\n"
            f"**Success Rate:** {int(data['success_rate'] * 100)}%\n"
            f"**Jail Time:** {format_cooldown_time(data['jail_time'], include_emoji=False)}\n"
            f"**Status:** {status}"
        )
    elif crime_type == "mugging":
        description = (
            f"{risk_emoji} **Risk Level:** {data['risk'].title()}\n"
            f"**Reward:** 15-25% of target's balance (max 1500)\n"
            f"**Success Rate:** {int(data['success_rate'] * 100)}%\n"
            f"**Jail Time:** {format_cooldown_time(data['jail_time'], include_emoji=False)}\n"
            f"**Status:** {status}"
        )
    else:
        description = (
            f"{risk_emoji} **Risk Level:** {data['risk'].title()}\n"
            f"**Reward:** {data['min_reward']}-{data['max_reward']}\n"
            f"**Success Rate:** {int(data['success_rate'] * 100)}%\n"
            f"**Jail Time:** {format_cooldown_time(data['jail_time'], include_emoji=False)}\n"
            f"**Status:** {status}"
        )
    
        
    return description
