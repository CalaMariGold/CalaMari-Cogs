import discord
import asyncio
import logging
from collections import defaultdict
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify, box
from typing import Optional, Dict, Any

# Unique identifier for Config
CONFIG_ID = 95932766180343809

# Default guild settings for Config
DEFAULT_GUILD: Dict[str, Any] = {
    "messages": {}, # message_id: {channel_id, total_count, emoji_counts: {emoji_str: count}}
    "include_nsfw": True, # Whether to include NSFW channels in global leaderboard
}

log = logging.getLogger("red.calamari.reactboard")

class ReactBoard(commands.Cog):
    """Leaderboard for message reactions using event listeners and Config."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=CONFIG_ID,
            force_registration=True,
        )
        self.config.register_guild(**DEFAULT_GUILD)

    # ------------------- Event Listeners ------------------- #

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handles reaction additions and updates Config."""
        if not payload.guild_id:
            return # Ignore DMs

        # Ignore reactions from the bot itself (optional, depends on desired behavior)
        # if payload.user_id == self.bot.user.id:
        #     return

        guild_id = payload.guild_id
        message_id = str(payload.message_id) # Config keys must be strings
        channel_id = payload.channel_id
        emoji_str = str(payload.emoji)

        async with self.config.guild_from_id(guild_id).messages() as messages:
            if message_id not in messages:
                messages[message_id] = {
                    "channel_id": channel_id,
                    "total_count": 0,
                    "emoji_counts": defaultdict(int)
                }
            elif "channel_id" not in messages[message_id]: # Handle potential old data format
                 messages[message_id]["channel_id"] = channel_id
                 messages[message_id]["total_count"] = 0
                 messages[message_id]["emoji_counts"] = defaultdict(int)

            # Update counts
            messages[message_id]["total_count"] += 1
            if isinstance(messages[message_id]["emoji_counts"], dict): # Ensure it's a defaultdict
                messages[message_id]["emoji_counts"] = defaultdict(int, messages[message_id]["emoji_counts"])
            messages[message_id]["emoji_counts"][emoji_str] += 1


    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handles reaction removals and updates Config."""
        if not payload.guild_id:
            return # Ignore DMs

        # Ignore reactions from the bot itself (optional)
        # if payload.user_id == self.bot.user.id:
        #     return

        guild_id = payload.guild_id
        message_id = str(payload.message_id)
        emoji_str = str(payload.emoji)

        async with self.config.guild_from_id(guild_id).messages() as messages:
            if message_id not in messages or emoji_str not in messages[message_id].get("emoji_counts", {}):
                # Message or specific emoji not tracked, nothing to remove
                # This can happen if the cog was loaded after the reaction was added
                return

            # Decrement counts
            messages[message_id]["total_count"] = max(0, messages[message_id].get("total_count", 1) - 1)
            if isinstance(messages[message_id]["emoji_counts"], dict):
                messages[message_id]["emoji_counts"] = defaultdict(int, messages[message_id]["emoji_counts"])
            
            messages[message_id]["emoji_counts"][emoji_str] = max(0, messages[message_id]["emoji_counts"].get(emoji_str, 1) - 1)

            # Clean up emoji if count is zero
            if messages[message_id]["emoji_counts"][emoji_str] == 0:
                del messages[message_id]["emoji_counts"][emoji_str]

            # Clean up message if total count is zero
            if messages[message_id]["total_count"] == 0:
                del messages[message_id]

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """Remove deleted messages from Config."""
        if not payload.guild_id:
            return

        message_id = str(payload.message_id)
        async with self.config.guild_from_id(payload.guild_id).messages() as messages:
            if message_id in messages:
                del messages[message_id]

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        """Remove bulk deleted messages from Config."""
        if not payload.guild_id:
            return

        message_ids = {str(msg_id) for msg_id in payload.message_ids}
        async with self.config.guild_from_id(payload.guild_id).messages() as messages:
            # Find keys to delete more efficiently
            keys_to_delete = message_ids.intersection(messages.keys())
            for key in keys_to_delete:
                del messages[key]

    # ------------------- Leaderboard Command ------------------- #

    @commands.command(aliases=["rb"])
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def reactboard(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel | discord.Thread] = None, # Added channel argument
        limit: commands.Range[int, 1, 25] = 10,
        emoji: Optional[str] = None
    ):
        """Shows the messages with the most reactions tracked by the cog.

        Optionally filter by a specific [channel].
        Use the optional [emoji] argument to filter by a specific emoji.
        The [limit] defaults to 10 (max 25).
        Data is updated via reaction events.
        """
        guild = ctx.guild
        if not guild:
            return

        # Use provided channel or None for guild-wide
        target_channel_id = channel.id if channel else None

        # Check user permissions if a specific channel is requested
        if channel:
            if not channel.permissions_for(ctx.author).view_channel:
                await ctx.send(f"You do not have permission to view the leaderboard for {channel.mention}.")
                return
            # Also check if bot can view the channel (it needs to fetch messages)
            if not channel.permissions_for(ctx.guild.me).view_channel:
                 await ctx.send(f"I do not have permission to view {channel.mention} to generate its leaderboard.")
                 return

        async with ctx.typing():
            # Fetch guild settings and message data
            guild_settings = await self.config.guild(guild).all()
            guild_messages_data = guild_settings.get("messages", {})
            include_nsfw = guild_settings.get("include_nsfw", True)

            if not guild_messages_data:
                await ctx.send("No reactions have been tracked yet.")
                return

            # Determine if NSFW filtering is needed
            filter_nsfw = not include_nsfw and not target_channel_id
            nsfw_channel_ids = set()
            if filter_nsfw:
                # Get all text/thread channels once and identify NSFW ones
                # Convert guild.threads SequenceProxy to list before concatenation
                all_channels = guild.text_channels + list(guild.threads)
                nsfw_channel_ids = {c.id for c in all_channels if getattr(c, 'is_nsfw', lambda: False)()}

            # Stores (message_id_int, channel_id, sort_value, total_count, emoji_counts_dict)
            leaderboard_data = []

            for msg_id_str, data in guild_messages_data.items():
                channel_id = data.get("channel_id")
                total_count = data.get("total_count", 0)
                emoji_counts = data.get("emoji_counts", {})

                # Apply channel filter if provided
                if target_channel_id and channel_id != target_channel_id:
                    continue

                # Apply NSFW filter if active
                if filter_nsfw and channel_id in nsfw_channel_ids:
                    continue

                if not channel_id or total_count <= 0:
                    continue

                sort_value = 0
                if emoji:
                    # If specific emoji requested, only include messages with that emoji
                    specific_emoji_count = emoji_counts.get(str(emoji), 0)
                    if specific_emoji_count > 0:
                        sort_value = specific_emoji_count
                    else:
                        continue # Skip if message doesn't have the requested emoji
                else:
                    # Otherwise, sort by total count
                    sort_value = total_count

                try:
                    leaderboard_data.append((int(msg_id_str), channel_id, sort_value, total_count, emoji_counts))
                except ValueError:
                    log.warning(f"Invalid message ID found in config for guild {guild.id}: {msg_id_str}")
                    continue # Skip invalid entry

            # Message if channel filter yields no results
            if not leaderboard_data:
                 no_results_msg = "No messages found"
                 if channel:
                     no_results_msg += f" in {channel.mention}"
                 if emoji:
                     no_results_msg += f" with the {emoji} reaction"
                 else:
                     no_results_msg += " with reactions"
                 no_results_msg += "."
                 await ctx.send(no_results_msg)
                 return


            # Sort by sort_value (either specific emoji count or total count) descending
            leaderboard_data.sort(key=lambda item: item[2], reverse=True)

            # Prepare embed
            channel_name_str = f" in {channel.mention}" if channel else ""
            title = f"🔥 Reaction Leaderboard{channel_name_str}" + (f" for {emoji}" if emoji else "")
            embed = discord.Embed(title=title, color=await ctx.embed_color())
            footer_text = f"Showing top {min(limit, len(leaderboard_data))} tracked messages"
            footer_text += f" in #{channel.name}" if channel else " in this server"
            embed.set_footer(text=footer_text)

            embed.description = None

            messages_processed = 0
            for msg_id, chan_id, sort_val, total_count, emoji_counts in leaderboard_data:
                if messages_processed >= limit:
                    break

                channel = guild.get_channel(chan_id)
                if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread)):
                    log.debug(f"Could not find channel {chan_id} for message {msg_id} in guild {guild.id}")
                    continue

                try:
                    message = await channel.fetch_message(msg_id)
                    author = message.author
                    link = message.jump_url
                    # Use a slightly longer snippet for context
                    content_snippet = message.content[:100].replace('\n', ' ') + ("..." if len(message.content) > 100 else "")

                    # Format emoji counts like: <:emoji:id> `count` | <emoji> `count`
                    if not emoji_counts:
                        reaction_str = "_No reactions tracked_"
                    else:
                        sorted_emojis = sorted(emoji_counts.items(), key=lambda item: item[1], reverse=True)
                        # Display more emojis in the new format
                        top_emojis = [f"{e} `{c}`" for e, c in sorted_emojis[:10]]
                        reaction_str = " | ".join(top_emojis)
                        if len(sorted_emojis) > 10:
                            reaction_str += " ..."


                    field_name = f"Rank #{messages_processed + 1} - {author.display_name}" if author else f"Rank #{messages_processed + 1} - Unknown User"
                    field_value = (
                        f"**User:** {author.mention if author else 'Unknown'}\n"
                        f"**Message:** {box(content_snippet) if content_snippet.strip() else '_No text content_'}\n"
                        f"**Reactions:** {reaction_str}\n"
                        f"[#{channel.name}]({link})"
                    )

                    # Check field value length (max 1024)
                    if len(field_value) > 1024:
                        # Truncate message snippet if value is too long
                        overflow = len(field_value) - 1024
                        max_snippet_len = 100 - overflow - 10 # Extra buffer
                        if max_snippet_len > 10:
                             content_snippet = message.content[:max_snippet_len].replace('\n', ' ') + "..."
                             field_value = (
                                f"**User:** {author.mention if author else 'Unknown'}\n"
                                f"**Message:** {box(content_snippet) if content_snippet.strip() else '_No text content_'}\n"
                                f"**Reactions:** {reaction_str}\n"
                                f"[#{channel.name}]({link})"
                             )
                        else: # Cannot shorten enough, skip field?
                             log.warning(f"Embed field value for msg {msg_id} too long even after shortening snippet.")
                             # Fallback: Just put a link?
                             field_value = f"[Link]({link}) - Content too long to display."

                    embed.add_field(name=field_name, value=field_value, inline=False)
                    messages_processed += 1

                except discord.NotFound:
                    log.debug(f"Message {msg_id} not found in channel {chan_id} (likely deleted).")
                    continue
                except discord.Forbidden:
                    log.warning(f"Missing permissions to fetch message {msg_id} or author info in channel {chan_id}.")
                    continue
                except discord.HTTPException as e:
                    log.error(f"HTTPException processing message {msg_id} in channel {chan_id}: {e}")
                    continue

            if messages_processed == 0:
                # This can happen if all top messages were deleted or inaccessible
                await ctx.send("Could not retrieve details for the top messages.")
                return

            # Send the embed with fields
            await ctx.send(embed=embed)

    # ------------------- Settings Commands ------------------- #

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def reactboardset(self, ctx: commands.Context):
        """Configure ReactBoard settings."""
        pass

    @reactboardset.command(name="nsfw")
    async def reactboardset_nsfw(self, ctx: commands.Context):
        """Toggle whether NSFW channels are included in the global leaderboard."""
        guild = ctx.guild
        current_setting = await self.config.guild(guild).include_nsfw()
        new_setting = not current_setting
        await self.config.guild(guild).include_nsfw.set(new_setting)
        status = "included" if new_setting else "excluded"
        await ctx.send(f"NSFW channels will now be {status} in the global leaderboard.")