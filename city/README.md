# City

A comprehensive city simulation system featuring a crime system with various activities, dynamic events, and an interactive button-based interface.

## Features

- 🦹 **Interactive Crime System**
  - Multiple crime types with varying risk levels and rewards
  - Dynamic success rates and cooldowns
  - Target-based crimes (pickpocket, mugging) with anti-farming measures
  - Random events that affect success rates and rewards
  - Jail system with bail and jailbreak mechanics

- 🎮 **Button-Based Interface**
  - Modern, intuitive button controls
  - Color-coded risk levels
  - Dynamic button states based on user status
  - Clean, organized menu system

- 📊 **Statistics & Leaderboards**
  - Track successful and failed crimes
  - Monitor lifetime earnings and largest heists
  - View server-wide crime leaderboards
  - Personal criminal status tracking

## Installation

1. Make sure you have Red-DiscordBot V3 installed
2. Add this repository: `[p]repo add CalaMari-Cogs https://github.com/CalaMariGold/CalaMari-Cogs`
3. Install the cog: `[p]cog install CalaMari-Cogs city`

## Setup

1. Load the cog: `[p]load city`
2. Make sure the bot has required permissions:
   - Manage Messages (for button interactions)
   - Send Messages
   - Embed Links
   - Add Reactions
3. Register your bank if not already done: `[p]bank register`
4. Customize settings as desired using the `[p]crimeset` commands

## Support

If you encounter any issues or have suggestions, please open an issue on the GitHub repository.

## Usage

### Crime Types

#### 🧤 Pickpocket
- Low risk, targeted crime
- Steal percentage of target's balance
- Quick cooldown
- Short jail time if caught

#### 🔪 Mugging
- Medium risk, targeted crime
- Steal percentage of target's balance
- Medium cooldown
- Moderate jail time

#### 🏪 Store Robbery
- Medium risk, non-targeted
- Fixed reward range
- Medium cooldown
- Moderate jail time

#### 🏛️ Bank Heist
- High risk, non-targeted
- Highest potential rewards
- Long cooldown
- Longest jail time

#### 🎲 Random Crime
- Random risk level
- Dynamic scenarios
- Varying rewards and penalties
- Unique events and outcomes

### Commands

**User Commands:**
- `[p]crime` - Open the main crime menu with all available actions
  - `commit` - Choose and commit a crime
  - `status` - View your criminal status and stats
  - `bail` - Pay to get out of jail early
  - `jailbreak` - Attempt to escape from jail
  - `leaderboard` - View the server's crime leaderboard
  - `notify` - Toggle jail release notifications

**Admin Commands:**
- `[p]crimeset` - Configure crime settings
  - `success_rate <crime_type> <rate>` - Set success rate (0.0 to 1.0)
  - `reward <crime_type> <min> <max>` - Set reward range
  - `cooldown <crime_type> <seconds>` - Set cooldown duration
  - `jailtime <crime_type> <seconds>` - Set jail time duration
  - `fine <crime_type> <multiplier>` - Set fine multiplier
  - `reload_defaults` - Reset to default settings
  - `global` - Configure global settings:
    - `bailcost <multiplier>` - Set bail cost multiplier
    - `togglebail <enabled>` - Enable/disable bail system
    - `notifycost <cost>` - Set notification unlock cost
    - `togglenotifycost <enabled>` - Enable/disable notification cost
    - `view` - View all current settings

**Owner Commands:**
- `[p]wipecitydata <user>` - Wipe a user's city data
- `[p]wipecityallusers` - Wipe ALL city data (requires confirmation)

## Configuration

### Global Settings
- `allow_bail` - Whether users can pay to get out of jail early
- `bail_cost_multiplier` - How much bail costs based on remaining time
- `min_steal_balance` - Minimum balance required to be targeted
- `max_steal_amount` - Maximum amount that can be stolen in one crime
- `notify_cost` - Cost to unlock jail release notifications
- `notify_cost_enabled` - Whether notifications require payment to unlock

### Per-Crime Settings
Each crime type can be configured with:
- Success rate (0.0 to 1.0)
- Reward range (min/max)
- Cooldown duration
- Jail time if caught
- Fine multiplier
- Whether it requires a target

## Requirements

- Red-DiscordBot V3
- Required Bot Permissions:
  - Manage Messages (for button interactions)
  - Send Messages
  - Embed Links
  - Add Reactions 