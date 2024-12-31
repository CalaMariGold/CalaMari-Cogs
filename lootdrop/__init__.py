"""
LootDrop cog for Red-DiscordBot by CalaMariGold
Random credit drops with good/bad outcomes
"""
from .lootdrop import LootDrop

__red_end_user_data_statement__ = "This cog stores user interaction cooldowns and statistics. No personal data is stored."

async def setup(bot):
    await bot.add_cog(LootDrop(bot))
