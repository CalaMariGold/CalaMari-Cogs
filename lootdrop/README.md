# LootDrop Cog for Red-DiscordBot

A fun and engaging cog that creates random loot drops in your Discord channels and threads. Users can claim rewards, build streaks, and participate in party drops with other members!

## Features

### Basic Functionality
- Random loot drops appear in configured channels and threads
- Customizable drop frequency and reward amounts
- Support for both text channels and threads
- Activity-based drops (only drops in active channels)
- Bad outcomes add risk/reward gameplay

### Streak System
- Earn streak bonuses for consecutive successful claims
- Configurable streak multipliers and timeouts
- Compete for highest streaks on the leaderboard
- Streaks reset on bad outcomes or timeout

### Party Drops
- Special drops that multiple users can claim
- Scaled rewards based on reaction time:
  - Super Fast (0-20%): 80-100% of max reward
  - Fast (20-40%): 60-80% of max reward
  - Medium (40-60%): 40-60% of max reward
  - Slow (60-80%): 20-40% of max reward
  - Very Slow (80-100%): minimum reward
- Configurable party drop chance and timeout

### Statistics & Leaderboard
- Track successful and failed claims
- View personal stats and streaks
- Server-wide leaderboard
- Rank tracking for competitive play

## Commands

### General Commands
- `[p]lootdrop` - Show basic cog info
- `[p]lootdrop stats [user]` - View loot drop statistics
- `[p]lootdrop leaderboard` - View the server leaderboard
- `[p]lootdrop settings` - View current settings

### Admin Commands
- `[p]lootdrop set toggle` - Enable/disable loot drops
- `[p]lootdrop set addchannel <channel/thread>` - Add a channel or thread
- `[p]lootdrop set removechannel <channel/thread>` - Remove a channel or thread
- `[p]lootdrop set credits <min> <max>` - Set credit range
- `[p]lootdrop set badchance <chance>` - Set bad outcome chance
- `[p]lootdrop set timeout <seconds>` - Set claim timeout
- `[p]lootdrop set frequency <min> <max>` - Set drop frequency
- `[p]lootdrop set activitytimeout <minutes>` - Set activity timeout
- `[p]lootdrop set streakbonus <percentage>` - Set streak bonus
- `[p]lootdrop set streakmax <max>` - Set maximum streak
- `[p]lootdrop set streaktimeout <hours>` - Set streak timeout
- `[p]lootdrop set partychance <chance>` - Set party drop chance
- `[p]lootdrop set partycredits <min> <max>` - Set party drop rewards
- `[p]lootdrop set partytimeout <seconds>` - Set party claim timeout
- `[p]lootdrop force [channel]` - Force a drop
- `[p]lootdrop forceparty [channel]` - Force a party drop

## Installation

1. Make sure you have Red-DiscordBot V3 installed
2. Add this repository: `[p]repo add CalaMari-Cogs https://github.com/CalaMariGold/CalaMari-Cogs`
3. Install the cog: `[p]cog install CalaMari-Cogs lootdrop`

## Setup

1. Load the cog: `[p]load lootdrop`
2. Add channels/threads: `[p]lootdrop set addchannel <channel/thread>`
3. Enable drops: `[p]lootdrop set toggle`
4. Customize settings as desired using the `[p]lootdrop set` commands

## Support

If you encounter any issues or have suggestions, please open an issue on the GitHub repository.

