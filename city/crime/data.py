"""Data and settings for the crime system."""

# Define available crimes and their properties
CRIME_TYPES = {
    "pickpocket": {
        "requires_target": True,
        "min_reward": 150,
        "max_reward": 500,
        "success_rate": 0.6,
        "cooldown": 300,  # 5 minutes
        "jail_time": 1800,  # 30 minutes if caught
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
        "cooldown": 600,  # 10 minutes
        "jail_time": 2700,  # 30 minutes if caught
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
        "jail_time": 2700,  # 45 minutes if caught
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
        "jail_time": 7200,  # 2 hours if caught
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
    "crime_options": CRIME_TYPES.copy(),  # Use the same crime types
    "global_settings": {
        "default_jail_time": 1800,  # 30 minutes
        "default_fine_multiplier": 0.5,
        "allow_bail": True,
        "bail_cost_multiplier": 0.35,  # Bail costs 0.35x the jail sentence
        "min_steal_balance": 100,  # Minimum balance required to be targeted
        "max_steal_amount": 1000,  # Maximum amount that can be stolen in one crime
        "protect_low_balance": True,  # Prevent stealing from users with very low balance
        "show_success_rate": True,  # Show success rate in crime messages
        "show_fine_amount": True,   # Show potential fine amounts
        "enable_random_events": True, # Enable random events during crimes
        "notify_cost": 10000,  # Cost to unlock notifications, 0 means free
        "notify_cost_enabled": True  # Whether notifications require payment to unlock
    }
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
}
