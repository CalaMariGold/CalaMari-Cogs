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

        # Set the OpenAI API key
        openai.api_key = self.config.api_key()

        # Load the model engine from the global config
        self.model_engine = self.config.model_engine()

        # Set the default model engine to use
        self.model_engine = "text-davinci-003"

        # Initialize a dictionary to store the bot's previous messages
        self.previous_messages = {}

    
    @commands.Cog.listener()
    async def on_message(self, message):
        try: 
            if message.author == self.bot.user or message.author.bot:
                return

            async def generate_image(input_text, message):
                prompt = f"{input_text}\n"
                response = openai.Image.create(model="image-alpha-001", prompt=prompt)
                image_url = response["data"][0]["url"]
                await message.channel.send(image_url)


            if message.reference:
                # This message is a reply to another message.
                # Check if the replied message is a message sent by the bot.
                replied_message = await message.channel.fetch_message(message.reference.resolved.id)
                if replied_message.author == self.bot.user:
                    # This is a reply to a message sent by the bot.
                    # Use the replied message as the previous message.
                    self.previous_messages[message.channel.id] = replied_message.content

                    async with message.channel.typing():
                        # Check if the message includes the "generate an image of" command
                        # Compile the regex pattern with the re.IGNORECASE flag
                        pattern = re.compile(r"generate an image of (.*)", re.IGNORECASE)
                        
                        # Check if the message matches the regex pattern
                        match = pattern.search(message.content)
                        if match:
                            # Get the input from the message
                            input_text = match.group(1)
                            
                            # Use Dall-E to generate an image
                            await generate_image(input_text, message)
                        else:
                            # Use ChatGPT to generate a response to the message
                            model_engine = self.model_engine

                            baa_mention = "<@791424813049970738>"
                            # Remove all instances of the bot's user mention from the message content
                            message.content = message.content.replace(baa_mention, "")

                            prompt = (f"You are Baa, a member of the Discord server {message.guild.name}. Your previous message was: \"{self.previous_messages}\" Reply to this message from {message.author.nick if message.author.nick else message.author.name}: {message.content}\n")

                            completions = openai.Completion.create(engine=model_engine, prompt=prompt, max_tokens=1024, n=1,stop=None,temperature=1.0)
                            response = completions.choices[0].text
                            
                            # Split the response into chunks of 2000 characters or fewer
                            chunk_size = 2000
                            chunks = [response[i:i+chunk_size] for i in range(0, len(response), chunk_size)]
                        
                            message_ids = []
                            # Send the chunks as separate messages
                            for chunk in chunks:
                                reply = await message.reply(chunk)
            elif self.bot.user in message.mentions:
                    async with message.channel.typing():
                        # Check if the message includes the "generate an image of" command
                        # Compile the regex pattern with the re.IGNORECASE flag
                        pattern = re.compile(r"generate an image of (.*)", re.IGNORECASE)
                        
                        # Check if the message matches the regex pattern
                        match = pattern.search(message.content)
                        if match:
                            # Get the input from the message
                            input_text = match.group(1)
                            
                            # Use Dall-E to generate an image
                            await generate_image(input_text, message)
                        else:
                            # Use ChatGPT to generate a response to the message
                            model_engine = self.model_engine

                            baa_mention = "<@791424813049970738>"
                            # Remove all instances of the bot's user mention from the message content
                            message.content = message.content.replace(baa_mention, "")

                            prompt = (f"You are Baa, a member of the Discord server {message.guild.name}. Reply to this message from {message.author.nick if message.author.nick else message.author.name}: {message.content}\n")

                            completions = openai.Completion.create(engine=model_engine, prompt=prompt, max_tokens=1024, n=1,stop=None,temperature=1.0)
                            response = completions.choices[0].text
                            
                            # Split the response into chunks of 2000 characters or fewer
                            chunk_size = 2000
                            chunks = [response[i:i+chunk_size] for i in range(0, len(response), chunk_size)]
                        
                            message_ids = []
                            # Send the chunks as separate messages
                            for chunk in chunks:
                                reply = await message.reply(chunk)
        except Exception as e:
                    # Output an error message if an exception occurred
                    await message.channel.send(f"An error occurred: {e}")

    @commands.group()
    async def chatgpt(self, ctx):
        # This command has no implementation, but it's needed as the parent command
        # for the subcommands.
        pass


    @chatgpt.command()
    async def setmodel(self, ctx, model_engine: str):
        # Set the model engine in the cog
        self.model_engine = model_engine
    
        # Save the model engine to the global config
        await self.config.model_engine.set(self.model_engine)
        
        # Send a confirmation message to the user
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
        
        # Send a confirmation message to the user
        await ctx.send(f"API key set.")


    @chatgpt.command()
    async def listmodels(self, ctx):
        # Get a list of the available models
        models = openai.Engine.list()["data"]
        
        # Build the response message
        response = "Available models:\n"
        for model in models:
            response += f"- {model['id']}\n"
        
        # Send the response message to the user
        await ctx.send(response)


def setup(bot):
    bot.add_cog(ChatGPT(bot))