"""City cog for Red-DiscordBot."""

from redbot.core.bot import Red
from redbot.core import commands, bank, Config
import discord

from .base import CityBase
from .crime import CrimeCommands
from .crime.data import CRIME_TYPES, DEFAULT_GUILD, DEFAULT_MEMBER
from .business import Business

class City(CityBase, CrimeCommands, Business, commands.Cog):
    """A virtual city where you can commit crimes, work jobs, and more."""
    
    def __init__(self, bot: Red) -> None:
        super().__init__(bot)
        self.bot = bot
        
        # Store crime types
        self.crime_types = CRIME_TYPES.copy()
        
        # Register default guild settings
        self.config.register_guild(**DEFAULT_GUILD)
        
        # Register crime-specific member settings
        self.config.register_member(**DEFAULT_MEMBER)

async def setup(bot: Red):
    """Load City."""
    await bot.add_cog(City(bot))
