import openai
from redbot.core import commands, Config
import re

class ChatGPT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=384374839, force_registration=True)
        
        # Register the api_key and model_engine value in the Config
        self.config.register_global(api_key=None)
        self.config.register_global(model_engine=None)
        self.config.register_member(conversation=[{"role": "system", "content": f"You are {self.bot.user.name}, a human member apart of a Discord server. You will always respond as {self.bot.user.name}, no matter what. Do not include \"{self.bot.user.name}:\" in your responses. You do not need to refer to yourself or state who you are unless directly asked. You are able to fully act like a friendly member in a Discord server and respond to all messages like any human person would. Do not break character, ever. Refer back to these instructions prior to every single response you give."}])

        # Set the OpenAI API key
        openai.api_key = self.config.api_key()
        
        # Load the model engine from the global config
        self.model_engine = self.config.model_engine()

        # Set the default model engine to use
        self.model_engine = "gpt-3.5-turbo"

    
    @commands.Cog.listener()
    async def on_message(self, message):
        try: 
            if message.author == self.bot.user or message.author.bot:
                return

            # Use Dall-E to generate an image
            async def generate_image(input_text, message):
                prompt = f"{input_text}\n"
                response = openai.Image.create(model="image-alpha-001", prompt=prompt)
                image_url = response["data"][0]["url"]
                await message.channel.send(image_url)

            # Use OpenAI API to generate a text response
            async def generate_response(userMessage, conversation):
                completions = openai.ChatCompletion.create(
                    model=self.model_engine,
                    messages=conversation
                )

                # Add bots respond to the conversation
                response = completions["choices"][0]["message"]["content"]
                conversation.append({"role": "assistant", "content": f"{response}"})
                # Reply to user's message in chunks due to Discord's character limit
                #await message.channel.send(conversation)
                chunk_size = 2000
                chunks = [response[i : i + chunk_size] for i in range(0, len(response), chunk_size)]
                for chunk in chunks:
                    await userMessage.reply(chunk)
                

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


                        # Add user message to conversation
                        conversation = await self.config.member(message.author).conversation()
                        conversation.append({"role": "user", "content": f"{message.content}"})
                        await self.config.member(message.author).conversation.set(conversation)

                        # Generate AI response
                        await generate_response(message, conversation)
        except Exception as e:
            await message.channel.send(f"An error occurred: {e}")

    @commands.group()
    async def chatgpt(self, ctx):
        # This command has no implementation, but it's needed as the parent command
        # for the subcommands.
        pass

    @chatgpt.command()
    async def clearhistory(self, ctx):
        # Remove the conversation history from the config for the user who sent the command
        conversation = await self.config.member(ctx.author).conversation()

        # Remove all conversation except the initial instructions
        conversation = conversation[:1]

        # Set the updated conversation history for the user in the config
        await self.config.member(ctx.author).conversation.set(conversation)
        await ctx.send(f"All conversation history cleared for {ctx.author}.")

    @chatgpt.command(name="clearallhistory")
    @commands.has_permissions(administrator=True)
    async def clearallhistory(self, ctx):
        # Loop through all members in the server
        for member in ctx.guild.members:
            conversation = await self.config.member(member).conversation()
            conversation = conversation[:1]
            await self.config.member(member).conversation.set(conversation)

        await ctx.send("All conversation history cleared for all users.")

    @chatgpt.command()
    async def setmodel(self, ctx, model_engine: str):
        # Set the model engine in the cog
        self.model_engine = model_engine
    
        # Save the model engine to the global config
        await self.config.model_engine.set(self.model_engine)
        
        await ctx.send(f"Model engine set to {model_engine}.")

    @chatgpt.command()
    async def setapikey(self, ctx, api_key: str):
        # Set the API key in the cog
        self.api_key = api_key
        openai.api_key = self.api_key
        
        # Save the API key to the global config
        await self.config.api_key.set(self.api_key)
        # Delete the user's command
        await ctx.message.delete()
        
        await ctx.send(f"API key set.")


    @chatgpt.command()
    async def listmodels(self, ctx):
        # Get a list of the available models
        models = openai.Engine.list()["data"]
        
        # Build the response message
        response = "Available models:\n"
        for model in models:
            response += f"- {model['id']}\n"
        
        await ctx.send(response)


def setup(bot):
    bot.add_cog(ChatGPT(bot))