# This init is required for each cog.
# Import your main class from the cog's folder.
from .chatgpt import ChatGPT


def setup(bot):
    bot.add_cog(ChatGPT(bot))
