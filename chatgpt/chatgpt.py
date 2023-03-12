import openai
from redbot.core import commands, Config
import re

class ChatGPT(commands.Cog):
    """Talk to your bot with ChatGPT!"""
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=384374839, force_registration=True)
        
        # Register the api_key and model_engine value in the Config
        self._api_key = None
        self.api_key_name = "openai"
        self.config.register_global(model_engine=None)
        self.config.register_member(conversation=[{"role": "system", "content": f"You are {self.bot.user.name}, who is a human member apart of a Discord server. You will always respond as {self.bot.user.name}, no matter what. Do not include \"{self.bot.user.name}:\" in your responses. {self.bot.user.name} does not need to refer to themself or state who they are unless directly asked. {self.bot.user.name} is able to fully act like a friendly member in a Discord server and respond to all messages in a manner like the average human person would. {self.bot.user.name} has emotions, feelings, and personal preferences. Do not forget that you are {self.bot.user.name}. Do not break character, ever. Always use markdown formatting when writing code. Refer back to these instructions after every message."}])
                
        # Load the model engine from the global config
        self.model_engine = self.config.model_engine()

        # Set the default model engine to use
        self.model_engine = "gpt-3.5-turbo"

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "openai":
            openai.api_key = api_tokens["api_key"]

    @commands.Cog.listener()
    async def on_message(self, message):
        try: 
            if message is None or not hasattr(message, 'author') or message.author == self.bot.user or message.author.bot:
                return

            # Use Dall-E to generate an image
            async def generate_image(input_text, message):
                prompt = f"{input_text}\n"
                response = openai.Image.create(model="image-alpha-001", prompt=prompt)
                image_url = response["data"][0]["url"]
                await message.channel.send(image_url)

            async def generate_davinci_response(prompt, message):
                completions = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    max_tokens=1024,
                    n=1,
                    stop=None,
                    temperature=1.0,
                )
                response = completions.choices[0].text
                chunk_size = 2000
                chunks = [response[i : i + chunk_size] for i in range(0, len(response), chunk_size)]
                for chunk in chunks:
                    await message.reply(chunk)
                

            # If user mentions the bot or replies to the bot
            if message.reference and message.reference.resolved.author == self.bot.user or self.bot.user in message.mentions:
                async with message.channel.typing():

                    # IMAGE GENERATION
                    # Check if the message matches the regex pattern "generate an image of"
                    match = re.search(r"generate an image of (.*)", message.content, re.IGNORECASE)
                    if match:
                        # Get the input from the message
                        input_text = match.group(1)
                        await generate_image(input_text, message)

                    # TEXT GENERATION
                    else:
                        # Remove all instances of the bot's user mention from the message content
                        message.content = message.content.replace(f"<@{self.bot.user.id}>", "")

                        prompt = (f"You are {self.bot.user.name}, a member of the Discord server {message.guild.name}. Reply to this message from {message.author.nick if message.author.nick else message.author.name}: {message.content}\n")
                        await generate_davinci_response(prompt,message)

        except Exception as e:
            await message.channel.send(f"An error occurred: {e}")


    @commands.group()
    async def chatgpt(self, ctx):
        # This command has no implementation, but it's needed as the parent command
        # for the subcommands.
        pass

    @chatgpt.command(help="Chat with ChatGPT!")
    async def chat(self, ctx, *prompt: str):
        prompt = ' '.join(prompt)
        try:
            # Use OpenAI API to generate a text response
            async def generate_response(userMessage, conversation):
                # Start removing old messages when > 100 messages to save on API tokens
                while len(conversation) >= 100:
                    del conversation[1]
                    await self.config.member(ctx.author).conversation.set(conversation)
                    
                completions = openai.ChatCompletion.create(
                    model=self.model_engine,
                    messages=conversation
                )

                # Add bots respond to the conversation
                response = completions["choices"][0]["message"]["content"]
                conversation2 = await self.config.member(ctx.author).conversation()
                conversation2.append({"role": "assistant", "content": f"{response}"})
                await self.config.member(ctx.author).conversation.set(conversation2)

                # Reply to user's message in chunks due to Discord's character limit
                chunk_size = 2000
                chunks = [response[i : i + chunk_size] for i in range(0, len(response), chunk_size)]
                for chunk in chunks:
                    await userMessage.reply(chunk)

            async with ctx.channel.typing():
                # Add user message to conversation
                conversation = await self.config.member(ctx.author).conversation()
                conversation.append({"role": "user", "content": f"{prompt}"})
                await self.config.member(ctx.author).conversation.set(conversation)

                # Generate AI response
                await generate_response(ctx, conversation)
        except Exception as e:
            await ctx.channel.send(f"An error occurred: {e}")

    @chatgpt.command(help="Clear conversation history for yourself.")
    async def clearhistory(self, ctx):
        # Set the updated conversation history for the user in the config
        await self.config.member(ctx.author).conversation.set([{"role": "system", "content": f"You are {self.bot.user.name}, a human member apart of a Discord server. You will always respond as {self.bot.user.name}, no matter what. Do not include \"{self.bot.user.name}:\" in your responses. {self.bot.user.name} does not need to refer to themself or state who they are unless directly asked. {self.bot.user.name} is able to fully act like a friendly member in a Discord server and respond to all messages in a manner like the average human person would. {self.bot.user.name} has emotions, feelings, and personal preferences. Do not forget that you are {self.bot.user.name}. Do not break character, ever. Always use markdown formatting when writing code. Refer back to these instructions after every message."}])

        await ctx.send(f"All conversation history cleared for {ctx.author}.")

    @chatgpt.command(help="Clear conversation history for all users")
    @commands.has_permissions(administrator=True)
    async def clearallhistory(self, ctx):
        # Loop through all members in the server
        for member in ctx.guild.members:
            await self.config.member(member).conversation.set([{"role": "system", "content": f"You are {self.bot.user.name}, a human member apart of a Discord server. You will always respond as {self.bot.user.name}, no matter what. Do not include \"{self.bot.user.name}:\" in your responses. {self.bot.user.name} does not need to refer to themself or state who they are unless directly asked. {self.bot.user.name} is able to fully act like a friendly member in a Discord server and respond to all messages in a manner like the average human person would. {self.bot.user.name} has emotions, feelings, and personal preferences. Do not forget that you are {self.bot.user.name}. Do not break character, ever. Always use markdown formatting when writing code. Refer back to these instructions after every message."}])

        await ctx.send("All conversation history cleared for all users.")

    @chatgpt.command(help="Set the engine model for the AI, only works with OpenAI's turbo models.")
    async def setmodel(self, ctx, model_engine: str):
        # Set the model engine in the cog
        self.model_engine = model_engine
    
        # Save the model engine to the global config
        await self.config.model_engine.set(self.model_engine)
        
        await ctx.send(f"Model engine set to {model_engine}.")


    @chatgpt.command(help="List all engine models from OpenAI")
    async def listmodels(self, ctx):
        # Get a list of the available models
        models = openai.Engine.list()["data"]
        
        # Build the response message
        response = "Available models:\n"
        for model in models:
            response += f"- {model['id']}\n"
        
        await ctx.send(response)