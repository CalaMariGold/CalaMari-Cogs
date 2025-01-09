# Business System - City Cog

## Overview
The business system is a dynamic economic feature that allows players to establish and manage their own businesses within the city. Players can earn passive income, upgrade their establishments, and engage in strategic risk management. The system incorporates elements of passive income generation, player interaction through robberies (via the crime module), and progressive advancement through multiple business levels and industries.

Key aspects:
- Passive income through a vault-based system
- Three distinct industry types with unique mechanics
- Upgradeable business levels with increasing benefits
- Strategic security vs. profit decisions
- Interactive robbery system for player engagement
- Shop system with progressive unlocks

## 🏢 Core Features

### 💰 Passive Income Generation
- Deposit credits into your business vault
- Earn daily profits based on vault balance
- Business vault can be robbed by players, stealing a percentage of the vault balance
- Strategic risk vs. reward management

### 🏦 Vault System
- Put credits in your vault to earn profit
- Every hour you get 1/24th of your daily rate
- Profits automatically add to your vault
- More credits in vault = more profit per hour
- Anyone can try to rob your vault
- Vault has a maximum capacity based on level
- Choose between collecting profits or letting them compound

Example:
- You have a Level 1 business (2% daily rate)
- You put 10,000 credits in your vault
- Each hour you earn: 10,000 × (2% ÷ 24) = 8.33 credits
- After one day: ~200 credits profit
- Profits add to your vault automatically every hour

### ⬆️ Business Progression and Shop
- Multiple upgrade levels with increased vault capacity
- Better income generation rates at higher levels
- Access to better shop items, including security upgrades
- Level-gated special items
- Mix of defensive and profit-focused items

## Business Industries

Choose your industry when starting (expensive to change later):

### 💹 Trading
- Daily profit rate fluctuates between -10% to +10% of base rate, +5% both ways for each level
- Rate changes at midnight server time
- 24h lockup period after deposits (no withdrawals)
- Each day with increased profit adds +1% to base rate (max +10% bonus)
- Bonus persists until a day with negative rate
- Best for players who enjoy active management and timing
- Example: At level 1 (2% base), rate varies from 1.7% to 2.3% daily

### 🏭 Manufacturing
- Base profit rate: -1% from the base rate (1% profit rate at lv 1)
- Vault capacity +25% (Level 1: 37.5k instead of 30k)
- Robbery steal % reduced by 15% (steal 8.5-21.25% instead of 10-25%)
- Consecutive days without withdrawal adds +0.5% profit (max +10%)
- Best for players who prefer steady, long-term growth

### 🎯 Retail
- Base profit rate +35%
- Robbery success rate increases by 15%
- Each successful robbery reduces profit rate by 5% for 24hr
- Robbery penalties stack up to -15% maximum
- Best for players who prefer high risk, high reward

## Business Levels

### Level 1
- Max vault: 30,000 credits
- Income rate: 2% daily
- Access to basic shop items

### Level 2
- Max vault: 75,000 credits
- Income rate: 2.5% daily
- Unlocks intermediate shop items

### Level 3
- Max vault: 150,000 credits
- Income rate: 3% daily
- Unlocks advanced shop items

### Level 4
- Max vault: 300,000 credits
- Income rate: 3.5% daily
- Unlocks premium shop items

## Shop Items

### Level 1 Items
- 📷 Security Camera (-10% robbery success) - 10,000 credits
- 🚨 Basic Alarm (-10% robbery success) - 15,000 credits

### Level 2 Unlocks
- 💂 Security Guard (-15% robbery success) - 25,000 credits
- 🏦 Vault Insurance (recover 25% of stolen credits) - 35,000 credits

### Level 3 Unlocks
- 🛡️ Advanced Security System (-20% robbery success) - 50,000 credits
- 📊 Risk Management (reduce max steal % by 5) - 75,000 credits

### Level 4 Unlocks
- 🔐 Premium Vault (25% of the vault is not considered for robbery percentage) - 100,000 credits
- 📈 Market Analyzer (+10% profit rate) - 125,000 credits

## Commands

### Business Owner Commands
- `[p]business` - Open the main business menu
  - `start <business name> <industry>` - Start a new business
  - `deposit <amount>` - Add credits to vault
  - `withdraw <amount>` - Remove credits from vault
  - `upgrade` - Level up your business
  - `shop` - View and purchase items
  - `status` - View business stats and info, including profit generated in the last 24 hours
  - `changeindustry <new_industry>` - Change business industry (costs 50% of your current max vault capacity)

### Criminal Commands
- `[p]crime commit business <target>` - Rob a business
  - Shows target's business level
  - Displays visible security measures
  - Indicates approximate vault balance
  - Shows success chance and potential steal amount

## System Mechanics

### Starting Out
- Players start a business with initial investment
- Choose an industry type that fits their playstyle
- Begin with basic shop items available

### Income Generation
- Larger vault balance = more daily profit
- Profits automatically add to vault balance
- All stored money (including profits) can be stolen
- Must balance growth vs. risk

### Business Robbery
- Criminals can target a business vault once every 24 hours
- Base steal range: 5-15% of vault balance
- Vaults need a minimum of 2500 credits to be robbed
- Success chance calculation:
  - Start with 50% base chance
  - Add/subtract industry modifiers
  - Subtract target's security items
  - Add criminal's success rate items
- Steal percentage calculation:
  - Start with random 5-15% base steal
  - Subtract security item effects (Risk Management: -5%)
  - Subtract industry effects (Manufacturing: -15%)
  - Apply to vault balance
- Example:
  - Manufacturing business with Risk Management

### Progression
- Upgrade business level for better benefits
- Purchase shop items for security and profit
- Manage vault balance strategically
- Change industry for 50% of max vault capacity (Level 1: 15k, Level 2: 37.5k, Level 3: 75k, Level 4: 150k)