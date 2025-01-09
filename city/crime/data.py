"""Data and settings for the crime system."""

# Define available crimes and their properties
CRIME_TYPES = {
    "pickpocket": {
        "requires_target": True,
        "min_reward": 150,
        "max_reward": 500,
        "success_rate": 0.6,
        "cooldown": 600,  # 10 minutes
        "jail_time": 3600,  # 1 hour if caught
        "risk": "low",
        "enabled": True,
        "fine_multiplier": 0.35,  # 35% of max reward as fine
        "min_steal_percentage": 0.01,  # Steal 1-10% of target's credits
        "max_steal_percentage": 0.10
    },
    "mugging": {
        "requires_target": True,
        "min_reward": 400,
        "max_reward": 1500,
        "success_rate": 0.6,
        "cooldown": 1800,  # 30 minutes
        "jail_time": 5400,  # 1 hour 30 minutes if caught
        "risk": "medium",
        "enabled": True,
        "fine_multiplier": 0.4,  # 40% of max reward as fine
        "min_steal_percentage": 0.15,  # Steal 15-25% of target's credits
        "max_steal_percentage": 0.25
    },
    "rob_store": {
        "requires_target": False,
        "min_reward": 500,
        "max_reward": 2000,
        "success_rate": 0.5,
        "cooldown": 21600,  # 6 hours
        "jail_time": 10800,  # 3 hours if caught
        "risk": "medium",
        "enabled": True,
        "fine_multiplier": 0.4,  # 45% of max reward as fine
        "steal_percentage": 0
    },
    "bank_heist": {
        "requires_target": False,
        "min_reward": 1500,
        "max_reward": 5000,
        "success_rate": 0.4,
        "cooldown": 86400,  # 1 day
        "jail_time": 14400,  # 4 hours if caught
        "risk": "high",
        "enabled": True,
        "fine_multiplier": 0.4,  # 40% of max reward as fine
        "steal_percentage": 0
    },
    "random": {
        "requires_target": False,
        "min_reward": 100,  # Will be overridden by scenario
        "max_reward": 3000,  # Will be overridden by scenario
        "success_rate": 0.5,  # Will be overridden by scenario
        "cooldown": 3600,  # 1 hour
        "jail_time": 600,  # Will be overridden by scenario
        "risk": "random",  # Will be determined by scenario
        "enabled": True,
        "fine_multiplier": 0.5,  # Will be overridden by scenario
        "steal_percentage": 0
    }
}

# Default guild settings
DEFAULT_GUILD = {
    "crime_options": CRIME_TYPES,
    "global_settings": {
        "allow_bail": True,
        "bail_cost_multiplier": 1.6,
        "min_steal_balance": 100,
        "max_steal_amount": 1000,
        "default_jail_time": 1800,  # 30 minutes
        "default_fine_multiplier": 0.5,
        "protect_low_balance": True,  # Prevent stealing from users with very low balance
        "show_success_rate": True,  # Show success rate in crime messages
        "show_fine_amount": True,   # Show potential fine amounts
        "enable_random_events": True  # Enable random events during crimes
    },
    "custom_scenarios": []  # List to store custom scenarios for this guild
}

# Default member settings specific to crime
DEFAULT_MEMBER = {
    "jail_time": 0,  # Total time to serve
    "jail_started": 0,  # When jail time started
    "attempted_jailbreak": False,  # Whether attempted jailbreak this sentence
    "cooldowns": {},  # Crime cooldowns
    "total_successful_crimes": 0,
    "total_failed_crimes": 0,
    "total_fines_paid": 0,
    "total_credits_earned": 0,
    "largest_heist": 0,     # Track largest successful heist
    "total_stolen_from": 0, # Amount stolen from others
    "total_stolen_by": 0,   # Amount stolen by others
    "total_bail_paid": 0,   # Amount spent on bail
    "notify_on_release": False,  # Whether to ping user when jail sentence is over
    "current_streak": 0,    # Current successful crime streak
    "highest_streak": 0,    # Highest streak achieved
    "streak_multiplier": 1.0,  # Current reward multiplier from streak
}
