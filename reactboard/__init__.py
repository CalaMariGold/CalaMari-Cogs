from .reactboard import ReactBoard

async def setup(bot):
    """Load ReactBoard."""
    await bot.add_cog(ReactBoard(bot))
    pass