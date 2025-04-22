# ReactBoard

A cog for Red-DiscordBot that tracks message reactions and displays leaderboards.
!! CURRENTLY WIP !!

## Features

- **📊 Reaction Tracking:** Uses event listeners to efficiently track reactions added or removed from any message the bot can see.
- **🏆 Leaderboard Command:** Provides `[p]reactboard` (alias `[p]rb`) to show messages ranked by reaction count.
- **⚙️ Flexible Filtering:**
    - View server-wide leaderboard.
    - Filter leaderboard to a specific channel (`[p]reactboard #channel`).
    - Filter leaderboard by a specific emoji (`[p]reactboard [emoji]`).
    - Combine channel and emoji filters.
- **✨ Detailed Embed:** Displays leaderboard entries with:
    - Rank
    - Message Author
    - Message Snippet
    - Breakdown of top 10 reactions (e.g., `💖 \`5\` | 👍 \`3\``)
    - Link to the message using the channel name as text (`[#channel-name]`)
- **🔒 NSFW Channel Toggle:** Admins can toggle whether NSFW channels are included in the server-wide leaderboard using `[p]reactboardset nsfw`.
- **🧹 Automatic Pruning:** Reaction data for deleted messages is automatically removed.
- **🔐 Permission Checks:** Users can only view leaderboards for channels they have permission to see.

## Commands

### User Commands
- `[p]reactboard [channel] [limit] [emoji]` (Alias: `[p]rb`)
  - Shows the reaction leaderboard.
  - `[channel]`: (Optional) The specific channel or thread to show the leaderboard for. Defaults to the entire server.
  - `[limit]`: (Optional) The number of messages to show. Defaults to 10 (max 25).
  - `[emoji]`: (Optional) A specific emoji to filter and sort by. Defaults to total reactions.

### Admin Commands (`manage_guild` permission required)
- `[p]reactboardset nsfw`
  - Toggles whether NSFW channels are included in the server-wide leaderboard view.

## Installation

1. Make sure you have Red-DiscordBot V3 installed.
2. Add this repository: `[p]repo add CalaMari-Cogs https://github.com/CalaMariGold/CalaMari-Cogs`
3. Install the cog: `[p]cog install CalaMari-Cogs reactboard`

## Setup

1. Load the cog: `[p]load reactboard`
2. The cog will automatically start tracking reactions in channels the bot can see.
3. Use `[p]reactboardset nsfw` if you wish to exclude NSFW channels from the global view.
4. Ensure the bot has necessary permissions:
   - `View Channel` (in relevant channels to fetch messages for the leaderboard)
   - `Embed Links` (to display the leaderboard)

## Support

If you encounter any issues or have suggestions, please open an issue on the GitHub repository. 