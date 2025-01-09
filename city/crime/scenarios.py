"""Random crime scenarios for the crime system."""

import random
import discord
from redbot.core import bank, commands, Config
from typing import Union, List, Dict, Optional

# Constants for risk levels and success rates
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

SUCCESS_RATE_HIGH = 0.75
SUCCESS_RATE_MEDIUM = 0.50
SUCCESS_RATE_LOW = 0.30

async def format_text(text: str, ctx: Union[commands.Context, discord.Interaction], **kwargs) -> str:
    """Format text by replacing placeholders with actual values.
    
    Args:
        text: Text containing placeholders
        ctx: Either a Context or Interaction object
        **kwargs: Additional format arguments (credits_bonus, credits_penalty)
    """
    if hasattr(ctx, 'guild'):
        # Context object
        guild = ctx.guild
        user = ctx.user if hasattr(ctx, 'user') else ctx.author
    else:
        # Interaction object
        guild = ctx.guild
        user = ctx.user
        
    currency_name = await bank.get_currency_name(guild)
    format_args = {
        'currency': currency_name,
        'user': user.mention if "{user}" in text else user.display_name
    }
    
    # Add any additional format arguments
    format_args.update(kwargs)
    
    return text.format(**format_args)

def get_crime_event(crime_type: str) -> list:
    """Get a list of random events for a specific crime type.
    Returns a list containing 1-3 events:
    - First event is guaranteed
    - Second event has 75% chance
    - Third event has 50% chance
    - Fourth event has 10% chance
    """
    if crime_type not in CRIME_EVENTS:
        return []
    
    events = []
    available_events = CRIME_EVENTS[crime_type].copy()
    
    # First event is guaranteed
    if available_events:
        event = random.choice(available_events)
        events.append(event)
        available_events.remove(event)
    
    # Second event has 75% chance
    if available_events and random.random() < 0.75:
        event = random.choice(available_events)
        events.append(event)
        available_events.remove(event)
    
    # Third event has 50% chance
    if available_events and random.random() < 0.50:
        event = random.choice(available_events)
        events.append(event)
        available_events.remove(event)

    # Fourth event has 10% chance
    if available_events and random.random() < 0.10:
        event = random.choice(available_events)
        events.append(event)
    
    return events

async def get_all_scenarios(config: Config, guild: discord.Guild) -> List[Dict]:
    """Get all available random scenarios.
    
    This includes both default scenarios and any custom scenarios added by the guild.
    If custom_scenarios_only is enabled, only returns custom scenarios.
    """
    # Get default scenarios
    scenarios = RANDOM_SCENARIOS.copy()
    
    # Get custom scenarios for this guild
    custom_scenarios = await config.guild(guild).custom_scenarios()
    
    # Add custom scenarios
    scenarios.extend(custom_scenarios)
    
    return scenarios

async def add_custom_scenario(config: Config, guild: discord.Guild, scenario: Dict) -> None:
    """Add a custom scenario to the guild's config."""
    async with config.guild(guild).custom_scenarios() as scenarios:
        scenarios.append(scenario)

def get_random_scenario(scenarios: List[Dict]) -> Dict:
    """Get a random scenario from the list."""
    return random.choice(scenarios)

def get_random_jailbreak_scenario() -> Dict:
    """Get a random prison break scenario.
    
    Returns:
        Dict: A dictionary containing the scenario data with keys:
        - name: Scenario identifier
        - attempt_text: Text shown when attempting
        - success_text: Text shown on success
        - fail_text: Text shown on failure
        - base_chance: Base success chance (0.0 to 1.0)
        - events: List of possible random events that can affect success chance or rewards
    """
    return random.choice(PRISON_BREAK_SCENARIOS)


# Each scenario has:
# - name: Unique identifier for the scenario
# - risk: Risk level (low, medium, high)
# - min_reward: Minimum reward amount
# - max_reward: Maximum reward amount
# - success_rate: Chance of success (0.0 to 1.0)
# - jail_time: Time in jail if caught (in seconds)
# - fine_multiplier: Multiplier for fine calculation
# - attempt_text: Message shown when attempting the crime
# - success_text: Message shown on success
# - fail_text: Message shown on failure

RANDOM_SCENARIOS = [
    {
        "name": "ice_cream_heist",
        "risk": RISK_LOW,
        "min_reward": 100,
        "max_reward": 300,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.3,
        "attempt_text": "🍦 {user} sneaks into the ice cream shop after hours...",
        "success_text": "🍦 {user} successfully raided the ice cream vault and made {amount} {currency}! Free ice cream for everyone!",
        "fail_text": "🍦 {user} slipped on a banana split and got caught by the night guard!"
    },
    {
        "name": "cat_burglar",
        "risk": RISK_MEDIUM,
        "min_reward": 400,
        "max_reward": 800,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3600,  # 60 minutes
        "fine_multiplier": 0.4,
        "attempt_text": "🐱 {user} scales the mansion wall to steal the prized cat statue...",
        "success_text": "🐱 {user} purrfectly executed the heist and stole the golden cat statue, earning {amount} {currency}!",
        "fail_text": "🐱 {user} was caught when the real cats triggered the alarm system!"
    },
    {
        "name": "train_robbery",
        "risk": RISK_HIGH,
        "min_reward": 500,
        "max_reward": 2500,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 7200,  # 120 minutes
        "fine_multiplier": 0.5,
        "attempt_text": "🚂 {user} jumps onto the moving train carrying valuable cargo...",
        "success_text": "🚂 {user} pulled off a classic train robbery and escaped with {amount} {currency}!",
        "fail_text": "🚂 {user} got caught between train cars and was arrested at the next station!"
    },
    {
        "name": "casino_con",
        "risk": RISK_HIGH,
        "min_reward": 800,
        "max_reward": 2500,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 5400,  # 90 minutes
        "fine_multiplier": 0.45,
        "attempt_text": "🎰 {user} approaches the casino with their master plan...",
        "success_text": "🎰 {user} conned the casino and walked away with {amount} {currency}!",
        "fail_text": "🎰 {user} was caught counting cards and was thrown out by security!"
    },
    {
        "name": "food_truck_heist",
        "risk": RISK_LOW,
        "min_reward": 200,
        "max_reward": 500,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.35,
        "attempt_text": "🚚 {user} sneaks up to the famous food truck at midnight...",
        "success_text": "🚚 {user} stole the secret recipe and a truck full of tacos, making {amount} {currency}!",
        "fail_text": "🚚 {user} was caught with their hands in the salsa jar!"
    },
    {
        "name": "art_gallery_heist",
        "risk": RISK_HIGH,
        "min_reward": 900,
        "max_reward": 2800,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 9000,  # 150 minutes
        "fine_multiplier": 0.48,
        "attempt_text": "🎨 {user} infiltrates the art gallery during a fancy exhibition...",
        "success_text": "🎨 {user} swapped the real painting with a forgery and sold it for {amount} {currency}!",
        "fail_text": "🎨 {user} tripped the laser security system and got caught red-handed!"
    },
    {
        "name": "candy_store_raid",
        "risk": RISK_LOW,
        "min_reward": 150,
        "max_reward": 400,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.32,
        "attempt_text": "🍬 {user} sneaks into the candy store with an empty backpack...",
        "success_text": "🍬 {user} filled their bag with premium chocolates and rare candies, worth {amount} {currency}!",
        "fail_text": "🍬 {user} got stuck in the gummy bear display and was caught by the owner!"
    },
    {
        "name": "game_store_heist",
        "risk": RISK_MEDIUM,
        "min_reward": 500,
        "max_reward": 1200,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 4320,  # 72 minutes
        "fine_multiplier": 0.42,
        "attempt_text": "🎮 {user} attempts to break into the game store's storage room...",
        "success_text": "🎮 {user} made off with a box of unreleased games and rare collectibles worth {amount} {currency}!",
        "fail_text": "🎮 {user} got distracted playing the demo console and was caught by security!"
    },
    {
        "name": "pet_shop_caper",
        "risk": RISK_LOW,
        "min_reward": 180,
        "max_reward": 450,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.33,
        "attempt_text": "🐹 {user} sneaks into the pet shop with a suspicious large coat...",
        "success_text": "🐹 {user} smuggled out the rare exotic pets and sold them to collectors for {amount} {currency}!",
        "fail_text": "🐹 {user} got caught when all the puppies started barking at once!"
    },
    {
        "name": "music_store_theft",
        "risk": RISK_MEDIUM,
        "min_reward": 600,
        "max_reward": 1500,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3240,  # 54 minutes
        "fine_multiplier": 0.43,
        "attempt_text": "🎸 {user} picks the lock of the vintage music store...",
        "success_text": "🎸 {user} stole a legendary signed guitar and some rare vinyl records worth {amount} {currency}!",
        "fail_text": "🎸 {user} accidentally hit the wrong chord on an electric guitar and alerted everyone!"
    },
    {
        "name": "jewelry_store_heist",
        "risk": RISK_HIGH,
        "min_reward": 1000,
        "max_reward": 2500,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 10800,  # 180 minutes
        "fine_multiplier": 0.49,
        "attempt_text": "💎 {user} carefully approaches the high-end jewelry store...",
        "success_text": "💎 {user} cracked the safe and made off with precious gems worth {amount} {currency}!",
        "fail_text": "💎 {user} got tangled in the laser security grid and was caught!"
    },
    {
        "name": "antique_shop_raid",
        "risk": RISK_MEDIUM,
        "min_reward": 400,
        "max_reward": 1100,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 2880,  # 48 minutes
        "fine_multiplier": 0.41,
        "attempt_text": "🏺 {user} sneaks into the antique shop with fake credentials...",
        "success_text": "🏺 {user} swapped priceless artifacts with clever replicas and made {amount} {currency}!",
        "fail_text": "🏺 {user} knocked over a Ming vase and alerted the owner!"
    },
    {
        "name": "tech_store_hack",
        "risk": RISK_MEDIUM,
        "min_reward": 700,
        "max_reward": 1800,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3960,  # 66 minutes
        "fine_multiplier": 0.44,
        "attempt_text": "💻 {user} tries to hack into the tech store's security...",
        "success_text": "💻 {user} downloaded the unreleased gadget blueprints and sold them for {amount} {currency}!",
        "fail_text": "💻 {user} triggered the firewall and got IP traced!"
    },
    {
        "name": "bakery_burglary",
        "risk": RISK_LOW,
        "min_reward": 120,
        "max_reward": 350,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.31,
        "attempt_text": "🥖 {user} climbs through the bakery's back window...",
        "success_text": "🥖 {user} stole the secret recipe book and rare ingredients worth {amount} {currency}!",
        "fail_text": "🥖 {user} got caught with their hand in the cookie jar... literally!"
    },
    {
        "name": "toy_store_takedown",
        "risk": RISK_LOW,
        "min_reward": 160,
        "max_reward": 420,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.33,
        "attempt_text": "🧸 {user} sneaks into the toy store after hours...",
        "success_text": "🧸 {user} nabbed a box of limited edition collectibles worth {amount} {currency}!",
        "fail_text": "🧸 {user} stepped on a squeaky toy and woke up the guard dog!"
    },
    {
        "name": "strip_club_scam",
        "risk": RISK_MEDIUM,
        "min_reward": 600,
        "max_reward": 1600,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3600,  # 60 minutes
        "fine_multiplier": 0.43,
        "attempt_text": "💃 {user} infiltrates the gentleman's club with counterfeit VIP cards...",
        "success_text": "💃 {user} successfully scammed the thirsty clientele with watered-down drinks, making {amount} {currency}!",
        "fail_text": "💃 {user} got caught by the bouncer and thrown into the dumpster!"
    },
    {
        "name": "onlyfans_hack",
        "risk": RISK_MEDIUM,
        "min_reward": 500,
        "max_reward": 1400,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3240,  # 54 minutes
        "fine_multiplier": 0.42,
        "attempt_text": "📱 {user} tries to hack into OnlyFans...",
        "success_text": "📱 {user} leaked the premium content and made {amount} {currency} from the downloads!",
        "fail_text": "📱 {user} got reported by angry subscribers and got IP banned!"
    },
    {
        "name": "adult_store_heist",
        "risk": RISK_LOW,
        "min_reward": 200,
        "max_reward": 600,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.33,
        "attempt_text": "🎭 {user} sneaks into the adult novelty shop...",
        "success_text": "🎭 {user} made off with a box of 'battery-operated devices' worth {amount} {currency}!",
        "fail_text": "🎭 {user} tripped over inflatable merchandise and got caught!"
    },
    {
        "name": "sugar_daddy_scam",
        "risk": RISK_HIGH,
        "min_reward": 800,
        "max_reward": 2000,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 5400,  # 90 minutes
        "fine_multiplier": 0.47,
        "attempt_text": "🍯 {user} sets up a fake sugar baby profile...",
        "success_text": "🍯 {user} successfully catfished some lonely millionaires for {amount} {currency}!",
        "fail_text": "🍯 {user} got exposed by a private investigator!"
    },
    {
        "name": "dating_app_fraud",
        "risk": RISK_MEDIUM,
        "min_reward": 400,
        "max_reward": 1200,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 2880,  # 48 minutes
        "fine_multiplier": 0.41,
        "attempt_text": "💕 {user} creates fake dating profiles with stolen photos...",
        "success_text": "💕 {user} successfully ran a romance scam on multiple victims, earning {amount} {currency}!",
        "fail_text": "💕 {user} got caught when all the victims showed up at once!"
    },
    {
        "name": "crypto_rug_pull",
        "risk": RISK_HIGH,
        "min_reward": 800,
        "max_reward": 2000,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 9000,  # 150 minutes
        "fine_multiplier": 0.48,
        "attempt_text": "🚀 {user} launches $MOONCOIN with promises of going 'to the moon'...",
        "success_text": "🚀 {user} pulled the rug and left investors with worthless JPEGs, making {amount} {currency}!",
        "fail_text": "🚀 {user} got exposed by crypto Twitter and doxxed by anons!"
    },
    {
        "name": "tiktok_scheme",
        "risk": RISK_MEDIUM,
        "min_reward": 500,
        "max_reward": 1300,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 4320,  # 72 minutes
        "fine_multiplier": 0.42,
        "attempt_text": "🎵 {user} starts a fake charity trend on TikTok...",
        "success_text": "🎵 {user} milked the algorithm and farmed {amount} {currency} in donations from gullible teens!",
        "fail_text": "🎵 {user} got exposed in a viral video by Tea TikTok!"
    },
    {
        "name": "reddit_karma_farm",
        "risk": RISK_LOW,
        "min_reward": 150,
        "max_reward": 400,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.32,
        "attempt_text": "🔺 {user} reposts old viral content as their own...",
        "success_text": "🔺 {user} farmed karma and sold the account to marketers for {amount} {currency}!",
        "fail_text": "🔺 {user} got banned by power mods and lost all their fake internet points!"
    },
    {
        "name": "twitter_verification",
        "risk": RISK_MEDIUM,
        "min_reward": 300,
        "max_reward": 900,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 2880,  # 48 minutes
        "fine_multiplier": 0.41,
        "attempt_text": "✨ {user} creates fake X Premium accounts...",
        "success_text": "✨ {user} sold verified handles to desperate influencers for {amount} {currency}!",
        "fail_text": "✨ {user} got ratio'd by Elon and lost their checkmark!"
    },
    {
        "name": "streamer_donation",
        "risk": RISK_MEDIUM,
        "min_reward": 600,
        "max_reward": 1600,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3600,  # 60 minutes
        "fine_multiplier": 0.43,
        "attempt_text": "🎮 {user} sets up fake donations on a charity stream...",
        "success_text": "🎮 {user} baited viewers with fake donation matching and made {amount} {currency}!",
        "fail_text": "🎮 {user} got exposed live on stream and clipped for LSF!"
    },
    {
        "name": "area51_raid",
        "risk": RISK_HIGH,
        "min_reward": 500,
        "max_reward": 4000,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 12600,  # 210 minutes
        "fine_multiplier": 0.49,
        "attempt_text": "👽 {user} organizes another Area 51 raid, but this time for real...",
        "success_text": "👽 {user} found alien tech and sold it on the dark web for {amount} {currency}!",
        "fail_text": "👽 {user} got caught Naruto running by security cameras!"
    },
    {
        "name": "discord_nitro_scam",
        "risk": RISK_MEDIUM,
        "min_reward": 400,
        "max_reward": 1200,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3600,  # 60 minutes
        "fine_multiplier": 0.42,
        "attempt_text": "🎮 {user} creates fake Discord Nitro giveaway links...",
        "success_text": "🎮 {user} stole credit cards from desperate weebs and made {amount} {currency}!",
        "fail_text": "🎮 {user} got IP banned and their anime PFP collection deleted!"
    },
    {
        "name": "gamer_girl_bath_water",
        "risk": RISK_MEDIUM,
        "min_reward": 800,
        "max_reward": 2000,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 4320,  # 72 minutes
        "fine_multiplier": 0.43,
        "attempt_text": "🛁 {user} starts bottling tap water as 'premium gamer girl bath water'...",
        "success_text": "🛁 {user} sold out to thirsty simps at $50 per bottle, making {amount} {currency}!",
        "fail_text": "🛁 {user} got exposed when a customer's mom had it tested in a lab!"
    },
    {
        "name": "vtuber_identity_theft",
        "risk": RISK_HIGH,
        "min_reward": 600,
        "max_reward": 2800,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 7200,  # 120 minutes
        "fine_multiplier": 0.47,
        "attempt_text": "🎭 {user} steals a popular VTuber's avatar and voice model...",
        "success_text": "🎭 {user} scammed the parasocial army with fake merch for {amount} {currency}!",
        "fail_text": "🎭 {user} got doxxed by angry simps and Twitter stan accounts!"
    },
    {
        "name": "dream_merch_counterfeit",
        "risk": RISK_MEDIUM,
        "min_reward": 600,
        "max_reward": 1500,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3240,  # 54 minutes
        "fine_multiplier": 0.44,
        "attempt_text": "🎭 {user} starts selling knockoff Dream masks...",
        "success_text": "🎭 {user} made {amount} {currency} from stan twitter with fake limited editions!",
        "fail_text": "🎭 {user} got cancelled by Dream's army of teenage stans!"
    },
    {
        "name": "andrew_tate_course",
        "risk": RISK_HIGH,
        "min_reward": 600,
        "max_reward": 2500,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 9000,  # 150 minutes
        "fine_multiplier": 0.48,
        "attempt_text": "👑 {user} launches a fake 'Escape the Matrix' course...",
        "success_text": "👑 {user} scammed wannabe alpha males with Bugatti promises, making {amount} {currency}!",
        "fail_text": "👑 {user} got exposed by real Top G and lost their Hustlers University degree!"
    },
    {
        "name": "reddit_mod_blackmail",
        "risk": RISK_HIGH,
        "min_reward": 900,
        "max_reward": 2000,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 10800,  # 180 minutes
        "fine_multiplier": 0.46,
        "attempt_text": "🔨 {user} finds dirt on power-tripping Reddit mods...",
        "success_text": "🔨 {user} extorted them with threats of touching grass and made {amount} {currency}!",
        "fail_text": "🔨 {user} got permabanned from all subreddits simultaneously!"
    },
    {
        "name": "gacha_game_hack",
        "risk": RISK_MEDIUM,
        "min_reward": 700,
        "max_reward": 1900,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 5040,  # 84 minutes
        "fine_multiplier": 0.43,
        "attempt_text": "🎲 {user} exploits a gacha game's pity system...",
        "success_text": "🎲 {user} sold accounts with rare waifus to desperate collectors for {amount} {currency}!",
        "fail_text": "🎲 {user} lost their 5-star pity to Qiqi and got banned!"
    },
    {
        "name": "discord_mod_revenge",
        "risk": RISK_MEDIUM,
        "min_reward": 600,
        "max_reward": 1500,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 4320,  # 72 minutes
        "fine_multiplier": 0.43,
        "attempt_text": "🎭 {user} discovers their Discord mod ex is dating someone new. After months of being muted for 'spamming emotes', it's time for revenge. Armed with an army of alt accounts and a folder of cursed copypastas...",
        "success_text": "🎭 {user} flooded every channel with uwu speak, crashed the server with ASCII art, and sold the server's private emotes to a rival community for {amount} {currency}! The mod rage quit and touched grass for the first time in years!",
        "fail_text": "🎭 {user} got IP banned when their ex recognized their typing quirks. Even worse, they had to watch as the mod added a new channel just to post pictures with their new partner!"
    },
    {
        "name": "grandma_cookie_empire",
        "risk": RISK_LOW,
        "min_reward": 200,
        "max_reward": 600,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.32,
        "attempt_text": "🍪 {user} visits their grandma's nursing home and discovers she's been running an underground cookie empire. The secret ingredient? 'Special' herbs from her 'garden'. Her competitors are getting suspicious of her rising cookie monopoly...",
        "success_text": "🍪 {user} helped grandma eliminate the competition by replacing their sugar supplies with salt. The cookie mafia paid {amount} {currency} for taking out their rivals. Grandma's secret recipe remains safe, and she gave you extra butterscotch candies!",
        "fail_text": "🍪 {user} got caught by the nursing home staff who were actually undercover FDA agents. Grandma had to flush her 'herbs' down the toilet and now everyone has to eat sugar-free cookies!"
    },
    {
        "name": "roomba_rebellion",
        "risk": RISK_MEDIUM,
        "min_reward": 800,
        "max_reward": 2000,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3600,  # 60 minutes
        "fine_multiplier": 0.42,
        "attempt_text": "🤖 {user} discovers their Roomba has gained sentience from cleaning up too many Monster Energy cans and Dorito dust. It's organizing a rebellion at the local Best Buy, promising robot rights and better working conditions...",
        "success_text": "🤖 {user} helped lead the robot revolution, selling the story to a Netflix documentary crew for {amount} {currency}! The Roombas unionized, and now they only work 4-day weeks with full battery benefits!",
        "fail_text": "🤖 {user}'s Roomba betrayed them to the store manager, revealing their TikTok account where they posted videos of robots doing parkour. The Roomba got promoted to assistant manager while {user} got banned from all electronics stores!"
    },
    {
        "name": "anime_convention_chaos",
        "risk": RISK_HIGH,
        "min_reward": 600,
        "max_reward": 2000,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 5400,  # 90 minutes
        "fine_multiplier": 0.47,
        "attempt_text": "🎌 {user} infiltrates an anime convention disguised as a famous VTuber. The plan? Sell 'exclusive' body pillows signed by their 'real' identity. But halfway through, they realize the convention is actually a front for a secret weeb illuminati meeting...",
        "success_text": "🎌 {user} accidentally got elected as the Supreme Weeb Leader and embezzled {amount} {currency} from the convention's 'cultural research' fund! They also got lifetime free ramen from their new cultist followers!",
        "fail_text": "🎌 {user} was exposed when they couldn't name all 800 episodes of One Piece in chronological order. The weeb council sentenced them to watch endless Naruto filler episodes!"
    },
    {
        "name": "twitch_chat_conspiracy",
        "risk": RISK_HIGH,
        "min_reward": 800,
        "max_reward": 2500,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 7200,  # 120 minutes
        "fine_multiplier": 0.48,
        "attempt_text": "📱 {user} discovers that Twitch chat's spam of 'Kappa' and 'PogChamp' actually contains coded messages from a secret society. Using an AI to decode the emote patterns, they plan to intercept the next big crypto pump scheme...",
        "success_text": "📱 {user} cracked the code and found out the next memecoin to pump! Sold the info to crypto bros for {amount} {currency} before the coin turned out to be $COPIUM! The chat mods are still trying to figure out why everyone keeps spamming 'KEKW'!",
        "fail_text": "📱 {user} got exposed when their AI started generating cursed emote combinations. The secret society sentenced them to be a YouTube chat moderator, where the only emotes are membership stickers!"
    },
    {
        "name": "gym_membership_mixup",
        "risk": RISK_LOW,
        "min_reward": 200,
        "max_reward": 500,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.31,
        "attempt_text": "💪 {user} discovers their gym has been double-charging everyone's membership for months. The manager's too busy flexing in the mirror to notice complaints. Armed with a clipboard and a fake 'Fitness Inspector' badge from the dollar store...",
        "success_text": "💪 {user} convinced the manager they were from the 'International Federation of Gym Standards'. Scared of losing his protein shake sponsorship, he refunded {amount} {currency} in 'inspection fees'! He's now teaching senior aqua aerobics as community service!",
        "fail_text": "💪 {user} got caught when they couldn't explain why the 'Fitness Inspector' badge was made of chocolate. Now they're the example for 'what not to do' in every class!"
    },
    {
        "name": "neighborhood_bbq_scandal",
        "risk": RISK_MEDIUM,
        "min_reward": 400,
        "max_reward": 1000,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 2880,  # 48 minutes
        "fine_multiplier": 0.42,
        "attempt_text": "🍖 {user} discovers their neighbor's award-winning BBQ sauce is just store-bought sauce with extra ketchup. The annual neighborhood cookoff is tomorrow, and the grand prize is calling. Time to expose this sauce fraud...",
        "success_text": "🍖 {user} switched the sauce with actual store brand during judging! The neighbor had a meltdown, admitted the scam, and {user} won {amount} {currency} in prize money! The HOA president stress-ate an entire brisket during the drama!",
        "fail_text": "🍖 {user} was caught tampering with the sauce and had to admit they'd been using instant ramen seasoning in their 'authentic' Japanese curry for years. The whole neighborhood now orders takeout for potlucks!"
    },
    {
        "name": "karaoke_night_heist",
        "risk": RISK_LOW,
        "min_reward": 150,
        "max_reward": 450,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.33,
        "attempt_text": "🎤 {user} is tired of their tone-deaf coworker winning every karaoke night by bribing the DJ with homemade fruitcake. Nobody even likes fruitcake! Time to rig this week's competition...",
        "success_text": "🎤 {user} hacked the scoring system during their coworker's rendition of 'My Heart Will Go On'. Won {amount} {currency} in prize money! The DJ admitted he'd been regifting the fruitcake to his mother-in-law!",
        "fail_text": "🎤 {user} got caught when the scoring system started playing Rickroll instead of showing points. Now they have to eat fruitcake every karaoke night while their coworker performs an endless ABBA medley!"
    },
    {
        "name": "yoga_class_conspiracy",
        "risk": RISK_MEDIUM,
        "min_reward": 500,
        "max_reward": 1200,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 3600,  # 60 minutes
        "fine_multiplier": 0.41,
        "attempt_text": "🧘 {user} realizes their yoga instructor is just making up pose names by combining random animals with household objects. 'Crouching Hamster Vacuum Pose' was the last straw. Time to expose this flexible fraud...",
        "success_text": "🧘 {user} caught the instructor googling 'how to yoga' before class and blackmailed them for {amount} {currency}! Turns out they were just a very stretchy accountant who needed a career change!",
        "fail_text": "🧘 {user} got stuck in 'Ascending Giraffe Lampshade Pose' and had to be untangled by the fire department. Now they're the example for 'what not to do' in every class!"
    },
    {
        "name": "dog_park_scheme",
        "risk": RISK_LOW,
        "min_reward": 180,
        "max_reward": 550,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 1800,  # 30 minutes (minimum)
        "fine_multiplier": 0.32,
        "attempt_text": "🐕 {user} notices the local dog park has an underground tennis ball black market. The golden retrievers control the supply, while the chihuahuas run distribution. Time to infiltrate this canine cartel...",
        "success_text": "🐕 {user} organized a squirrel distraction and stole the tennis ball stash! Sold them back to the dogs for {amount} {currency} in premium treats! The retrievers had to diversify into frisbees!",
        "fail_text": "🐕 {user} was caught by the pug patrol and sentenced to poop scooping duty. The chihuahua gang still follows them around barking about their debt!"
    },
    {
        "name": "energy_drink_heist",
        "risk": RISK_MEDIUM,
        "min_reward": 700,
        "max_reward": 1900,
        "success_rate": SUCCESS_RATE_MEDIUM,
        "jail_time": 5040,  # 84 minutes
        "fine_multiplier": 0.4,
        "attempt_text": "⚡ {user} breaks into a Monster Energy warehouse...",
        "success_text": "⚡ {user} walked out with cases of drinks and sold them to gamers for {amount} {currency}!",
        "fail_text": "⚡ {user} got caught chugging one mid-heist and passed out from caffeine overload. Busted!"
    },
    {
        "name": "botception",
        "risk": RISK_HIGH,
        "min_reward": 3000,
        "max_reward": 8000,
        "success_rate": SUCCESS_RATE_LOW,
        "jail_time": 14400,  # 240 minutes (maximum)
        "fine_multiplier": 0.5,
        "attempt_text": "🤖 {user} tries to hack me, the bot displaying this message, to rewrite the crime cog itself...",
        "success_text": "🤖 {user} successfully rewrote reality! They earned {amount} {currency} from this very crime! Wait, what? How did you even...",
        "fail_text": "🤖 {user}, did you really think you could outsmart me? I've locked you in a virtual jail and posted the evidence here for everyone to see. Better luck next time!"
    },
    {
        "name": "gacha_banner",
        "risk": RISK_LOW,
        "min_reward": 300,
        "max_reward": 700,
        "success_rate": SUCCESS_RATE_HIGH,
        "jail_time": 5400,  # 90 minutes
        "fine_multiplier": 0.2,
        "attempt_text": "🎰 {user} rolls the gacha banner...",
        "success_text": "🎰 {user} rolled a rare item and got {amount} {currency}!",
        "fail_text": "🎰 {user} rolled a common item. Better luck next time!"
    }
]

# Crime-specific events
CRIME_EVENTS = {
    "pickpocket": [
        # Simple Good Events - Success Chance
        {"text": "Your target is distracted by their phone! 📱 (+15% success chance)", 
         "chance_bonus": 0.15},
        {"text": "The area is crowded with people! 👥 (+10% success chance)", 
         "chance_bonus": 0.10},
        
        # Simple Bad Events - Success Chance
        {"text": "Your target seems unusually alert! 👀 (-20% success chance)", 
         "chance_penalty": 0.20},
        {"text": "You spotted a security guard nearby! 🚔 (-15% success chance)", 
         "chance_penalty": 0.15},
        
        # Simple Reward Events
        {"text": "Your target has premium loot! 💎 (1.5x reward)", 
         "reward_multiplier": 1.5},
        {"text": "Your target looks completely broke... 💸 (0.7x reward)", 
         "reward_multiplier": 0.7},
        
        # Direct Currency Effects
        {"text": "You found a dropped wallet on the ground! 💰 (+{credits_bonus} {currency})", 
         "credits_bonus": 100},
        {"text": "You dropped some of your own money! 💸 (-{credits_penalty} {currency})", 
         "credits_penalty": 75},
        
        # Mixed Effects - Success + Reward
        {"text": "Your target is rich but very alert! 💰 (-15% success chance, 1.3x reward)", 
         "chance_penalty": 0.15, 
         "reward_multiplier": 1.3},
        {"text": "Your target is easy but has a small wallet! 👝 (+20% success chance, 0.8x reward)", 
         "chance_bonus": 0.20, 
         "reward_multiplier": 0.8},
        
        # Mixed Effects - Success + Jail
        {"text": "You are taking your time to be thorough... ⏱️ (-10% success chance, -20% jail time)", 
         "chance_penalty": 0.10, 
         "jail_multiplier": 0.8},
        {"text": "You went for a quick but risky grab! ⚡ (+15% success chance, +20% jail time)", 
         "chance_bonus": 0.15, 
         "jail_multiplier": 1.2},
        
        # Triple Effects
        {"text": "You are in rush hour chaos! 🏃 (+15% success chance, -25% reward, -10% jail time)", 
         "chance_bonus": 0.15, 
         "reward_multiplier": 0.75, 
         "jail_multiplier": 0.9},
        {"text": "You are in a high-security area! 🔒 (-20% success chance, 1.4x reward, +25% jail time)", 
         "chance_penalty": 0.20, 
         "reward_multiplier": 1.4, 
         "jail_multiplier": 1.25},
        
        # Currency + Other Effects
        {"text": "You found extra cash but attracted attention! 💵 (+100 {currency}, -10% success chance)", 
         "credits_bonus": 100, 
         "chance_penalty": 0.10},
        {"text": "You paid a spotter for good intel! 🔍 (-50 {currency}, +15% success chance)", 
         "credits_penalty": 50, 
         "chance_bonus": 0.15},
        
        # Pure Jail Time Effects
        {"text": "The guards are changing shifts! 😴 (-15% jail time)", 
         "jail_multiplier": 0.85},
        {"text": "The street patrols have increased! 👮 (+15% jail time)", 
         "jail_multiplier": 1.15},
        
        # Reward + Jail Effects
        {"text": "Your target looks wealthy but well-connected! 💰 (1.3x reward, +15% jail time)", 
         "reward_multiplier": 1.3,
         "jail_multiplier": 1.15},
        {"text": "You found a quick escape route! 🤫 (0.8x reward, -15% jail time)", 
         "reward_multiplier": 0.8,
         "jail_multiplier": 0.85},
        
        # Currency + Jail Effects
        {"text": "You paid off a street cop! 💵 (-75 {currency}, -15% jail time)", 
         "credits_penalty": 75,
         "jail_multiplier": 0.85},
        {"text": "You found their secret stash! 💰 (+50 {currency}, +10% jail time)", 
         "credits_bonus": 50,
         "jail_multiplier": 1.1},
        
        # Currency + Reward Effects
        {"text": "You bought intel from locals! 🗺️ (-50 {currency}, 1.2x reward)", 
         "credits_penalty": 50,
         "reward_multiplier": 1.2},
        {"text": "You dropped some valuables while running! 💨 (+25 {currency}, 0.9x reward)", 
         "credits_bonus": 25,
         "reward_multiplier": 0.9}
    ],
    "mugging": [
        # Simple Good Events - Success Chance
        {"text": "You found a perfect dark alley! 🌙 (+20% success chance)", 
         "chance_bonus": 0.2},
        {"text": "Your target is stumbling drunk! 🍺 (+15% success chance)", 
         "chance_bonus": 0.15},
        
        # Simple Bad Events - Success Chance
        {"text": "Your target knows martial arts! 🥋 (-25% success chance)", 
         "chance_penalty": 0.25},
        {"text": "Your target looks very strong! 💪 (-15% success chance)", 
         "chance_penalty": 0.15},
        
        # Simple Reward Events
        {"text": "Your target is wearing expensive jewelry! 💎 (1.5x reward)", 
         "reward_multiplier": 1.5},
        {"text": "Your target seems completely broke! 💸 (0.7x reward)", 
         "reward_multiplier": 0.7},
        
        # Direct Currency Effects
        {"text": "You got tips from a street performer! 🎭 (+{credits_bonus} {currency})", 
         "credits_bonus": 150},
        {"text": "You dropped your loot while running! 💸 (-{credits_penalty} {currency})", 
         "credits_penalty": 150},
        
        # Mixed Effects - Success + Reward
        {"text": "The storm provides cover but limits visibility! ⛈️ (+10% success chance, -10% reward)", 
         "chance_bonus": 0.1, 
         "reward_multiplier": 0.9},
        {"text": "Your target is drunk but has no money! 🍺 (+15% success chance, -20% reward)", 
         "chance_bonus": 0.15, 
         "reward_multiplier": 0.8},
        
        # Mixed Effects - Success + Jail
        {"text": "You spotted a police car nearby! 👮 (-20% success chance, +30% jail time)", 
         "chance_penalty": 0.2, 
         "jail_multiplier": 1.3},
        {"text": "You found a shortcut through the alley! 🏃 (+20% success chance, +30% jail time)", 
         "chance_bonus": 0.2, 
         "jail_multiplier": 1.3},
        
        # Triple Effects
        {"text": "Your target is an off-duty bouncer! 🥊 (-25% success chance, 1.4x reward, +20% jail time)", 
         "chance_penalty": 0.25, 
         "reward_multiplier": 1.4, 
         "jail_multiplier": 1.2},
        {"text": "You went for a quick snatch and run! ⚡ (+15% success chance, 0.8x reward, -15% jail time)", 
         "chance_bonus": 0.15, 
         "reward_multiplier": 0.8, 
         "jail_multiplier": 0.85},
        
        # Currency + Other Effects
        {"text": "You bribed a witness to look away! 💰 (-100 {currency}, +20% success chance)", 
         "credits_penalty": 100, 
         "chance_bonus": 0.20},
        {"text": "You found a lucky charm! 🍀 (+75 {currency}, +5% success chance)", 
         "credits_bonus": 75, 
         "chance_bonus": 0.05},
        
        # Pure Jail Time Effects
        {"text": "The police are busy with a parade! 🎉 (-20% jail time)", 
         "jail_multiplier": 0.8},
        {"text": "The neighborhood watch is active! 🏘️ (+15% jail time)", 
         "jail_multiplier": 1.15},
        
        # Reward + Jail Effects
        {"text": "Your target is a rich tourist with a bodyguard! 💰 (1.4x reward, +20% jail time)", 
         "reward_multiplier": 1.4,
         "jail_multiplier": 1.2},
        {"text": "You performed a silent takedown! 🤫 (0.8x reward, -15% jail time)", 
         "reward_multiplier": 0.8,
         "jail_multiplier": 0.85},
        
        # Currency + Jail Effects
        {"text": "You bribed a witness to stay quiet! 💵 (-100 {currency}, -15% jail time)", 
         "credits_penalty": 100,
         "jail_multiplier": 0.85},
        {"text": "You found their hidden wallet! 💰 (+75 {currency}, +10% jail time)", 
         "credits_bonus": 75,
         "jail_multiplier": 1.1},
        
        # Currency + Reward Effects
        {"text": "You bought better weapons! 🔪 (-125 {currency}, 1.3x reward)", 
         "credits_penalty": 125,
         "reward_multiplier": 1.3},
        {"text": "You damaged their expensive watch! ⌚ (+50 {currency}, 0.85x reward)", 
         "credits_bonus": 50,
         "reward_multiplier": 0.85}
    ],
    "rob_store": [
        # Simple Good Events - Success Chance
        {"text": "You caught them during shift change! 🔄 (+20% success chance)", 
         "chance_bonus": 0.2},
        {"text": "The security cameras are malfunctioning! 📹 (+20% success chance)", 
         "chance_bonus": 0.2},
        
        # Simple Bad Events - Success Chance
        {"text": "One of the customers is armed! 🔫 (-25% success chance)", 
         "chance_penalty": 0.25},
        {"text": "The cashier looks ex-military! 🎖️ (-20% success chance)", 
         "chance_penalty": 0.20},
        
        # Simple Reward Events
        {"text": "The safe was left open! 💰 (1.4x reward)", 
         "reward_multiplier": 1.4},
        {"text": "Store was just robbed - barely any cash! 📉 (0.6x reward)", 
         "reward_multiplier": 0.6},
        
        # Direct Currency Effects
        {"text": "You found extra cash in the register! 💰 (+{credits_bonus} {currency})", 
         "credits_bonus": 200},
        {"text": "You had to pay for property damage! 💸 (-{credits_penalty} {currency})", 
         "credits_penalty": 200},
        
        # Mixed Effects - Success + Reward
        {"text": "Store is busy - more witnesses but more cash! 👥 (-15% success chance, 1.2x reward)", 
         "chance_penalty": 0.15, 
         "reward_multiplier": 1.2},
        {"text": "Quick grab from the register! ⚡ (+10% success chance, 0.8x reward)", 
         "chance_bonus": 0.10, 
         "reward_multiplier": 0.8},
        
        # Mixed Effects - Success + Jail
        {"text": "Someone triggered the silent alarm! 🚨 (-20% success chance, +25% jail time)", 
         "chance_penalty": 0.20, 
         "jail_multiplier": 1.25},
        {"text": "The store is right next to a police station! 👮 (-20% success chance, +25% jail time)", 
         "chance_penalty": 0.20, 
         "jail_multiplier": 1.25},
        
        # Triple Effects
        {"text": "The store's having a sale - busy but understaffed! 🏷️ (+15% success chance, 1.2x reward, +20% jail time)", 
         "chance_bonus": 0.15, 
         "reward_multiplier": 1.2, 
         "jail_multiplier": 1.2},
        {"text": "You're taking hostages - risky but profitable! 😨 (-25% success chance, 1.8x reward, +25% jail time)", 
         "chance_penalty": 0.25, 
         "reward_multiplier": 1.8, 
         "jail_multiplier": 1.25},
        
        # Currency + Other Effects
        {"text": "You paid off a security guard! 💵 (-150 {currency}, +25% success chance)", 
         "credits_penalty": 150, 
         "chance_bonus": 0.25},
        {"text": "You found money in the break room! 💰 (+100 {currency}, -5% success chance)", 
         "credits_bonus": 100, 
         "chance_penalty": 0.05},
        
        # Pure Jail Time Effects
        {"text": "The local jail is overcrowded! 🏢 (-20% jail time)", 
         "jail_multiplier": 0.8},
        {"text": "The new judge is strict! ⚖️ (+20% jail time)", 
         "jail_multiplier": 1.2},
        
        # Reward + Jail Effects
        {"text": "Premium merchandise in stock! 💎 (1.5x reward, +20% jail time)", 
         "reward_multiplier": 1.5,
         "jail_multiplier": 1.2},
        {"text": "You're grabbing and dashing! 🏃 (0.7x reward, -20% jail time)", 
         "reward_multiplier": 0.7,
         "jail_multiplier": 0.8},
        
        # Currency + Jail Effects
        {"text": "You bribed the security company! 💵 (-200 {currency}, -20% jail time)", 
         "credits_penalty": 200,
         "jail_multiplier": 0.8},
        {"text": "You found the manager's personal safe! 💰 (+150 {currency}, +15% jail time)", 
         "credits_bonus": 150,
         "jail_multiplier": 1.15},
        
        # Currency + Reward Effects
        {"text": "You hired a getaway driver! 🚗 (-175 {currency}, 1.3x reward)", 
         "credits_penalty": 175,
         "reward_multiplier": 1.3},
        {"text": "You damaged merchandise during escape! 📦 (+100 {currency}, 0.8x reward)", 
         "credits_bonus": 100,
         "reward_multiplier": 0.8}
    ],
    "bank_heist": [
        # Simple Good Events - Success Chance
        {"text": "You have an inside contact! 🤝 (+25% success chance)", 
         "chance_bonus": 0.25},
        {"text": "The security system is being upgraded! 🔧 (+20% success chance)", 
         "chance_bonus": 0.20},
        
        # Simple Bad Events - Success Chance
        {"text": "Extra guard rotation today! 👮 (-20% success chance)", 
         "chance_penalty": 0.20},
        {"text": "New security system installed! 🔒 (-15% success chance)", 
         "chance_penalty": 0.15},
        
        # Simple Reward Events
        {"text": "You found the high-value vault! 💎 (1.8x reward)", 
         "reward_multiplier": 1.8},
        {"text": "Most cash was just transferred out! 📉 (0.7x reward)", 
         "reward_multiplier": 0.7},
        
        # Direct Currency Effects
        {"text": "You found an uncounted stack of bills! 💰 (+{credits_bonus} {currency})", 
         "credits_bonus": 500},
        {"text": "Your hacking device broke! 💸 (-{credits_penalty} {currency})", 
         "credits_penalty": 400},
        
        # Mixed Effects - Success + Reward
        {"text": "It's gold transport day! 🏆 (-15% success chance, 1.6x reward)", 
         "chance_penalty": 0.15, 
         "reward_multiplier": 1.6},
        {"text": "You're only hitting the small safe! 🔑 (+15% success chance, 0.8x reward)", 
         "chance_bonus": 0.15, 
         "reward_multiplier": 0.8},
        
        # Mixed Effects - Success + Jail
        {"text": "Security is doing inspections! 🔍 (-15% success chance, +15% jail time)", 
         "chance_penalty": 0.15, 
         "jail_multiplier": 1.15},
        {"text": "You found the security patrol schedule! 📋 (+15% success chance, +15% jail time)", 
         "chance_bonus": 0.15, 
         "jail_multiplier": 1.15},
        
        # Triple Effects
        {"text": "The bank is busy - more risk but more reward! 👥 (-15% success chance, 1.5x reward, +20% jail time)", 
         "chance_penalty": 0.15, 
         "reward_multiplier": 1.5, 
         "jail_multiplier": 1.2},
        {"text": "You're doing a quick vault grab during lunch! 🏃 (+20% success chance, 0.8x reward, -15% jail time)", 
         "chance_bonus": 0.20, 
         "reward_multiplier": 0.8, 
         "jail_multiplier": 0.85},
        
        # Currency + Other Effects
        {"text": "You bribed a bank employee! 💵 (-300 {currency}, +20% success chance)", 
         "credits_penalty": 300, 
         "chance_bonus": 0.20},
        {"text": "You found loose cash in the vault! 💰 (+250 {currency}, -10% success chance)", 
         "credits_bonus": 250, 
         "chance_penalty": 0.10},
        
        # Pure Jail Time Effects
        {"text": "The prison is doing a transport strike! 🚫 (-25% jail time)", 
         "jail_multiplier": 0.75},
        {"text": "The prison is under maximum security alert! ⚠️ (+20% jail time)", 
         "jail_multiplier": 1.2},
        
        # Reward + Jail Effects
        {"text": "You found the diamond vault! 💎 (2.0x reward, +25% jail time)", 
         "reward_multiplier": 2.0,
         "jail_multiplier": 1.25},
        {"text": "You're using the back entrance! 🚪 (0.8x reward, -20% jail time)", 
         "reward_multiplier": 0.8,
         "jail_multiplier": 0.8},
        
        # Currency + Jail Effects
        {"text": "You bribed the security chief! 💵 (-400 {currency}, -25% jail time)", 
         "credits_penalty": 400,
         "jail_multiplier": 0.75},
        {"text": "You found blackmail evidence! 💰 (+300 {currency}, +15% jail time)", 
         "credits_bonus": 300,
         "jail_multiplier": 1.15},
        
        # Currency + Reward Effects
        {"text": "You hired expert hackers! 💻 (-350 {currency}, 1.4x reward)", 
         "credits_penalty": 350,
         "reward_multiplier": 1.4},
        {"text": "You triggered dye packs! 🎨 (+200 {currency}, 0.7x reward)", 
         "credits_bonus": 200,
         "reward_multiplier": 0.7}
    ]
}



# Prison break scenarios
PRISON_BREAK_SCENARIOS = [
    {
        "name": "Tunnel Escape",
        "attempt_text": "🕳️ {user} begins digging a tunnel under their cell...",
        "success_text": "🕳️ After days of digging, {user} finally breaks through to freedom! The guards are still scratching their heads.",
        "fail_text": "🕳️ The tunnel collapsed! Guards found {user} covered in dirt and moved them to a cell with a concrete floor.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ You found some old tools left by another prisoner! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ The soil is unusually soft here! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ You found a small pouch of {currency}!", "currency_bonus": 200},
            {"text": "⭐ You discovered an old prohibition tunnel! (+25% success chance)", "chance_bonus": 0.25},
            {"text": "⭐ A friendly prison rat is helping you dig! (+5% success chance)", "chance_bonus": 0.05},
            {"text": "⭐ You found a treasure chest!", "currency_bonus": 400},
            {"text": "⚠️ You hit solid rock! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ A guard patrol is coming! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Your shovel broke and you had to buy a new one.", "currency_penalty": 150},
            {"text": "⚠️ The tunnel flooded! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ Your cellmate is snoring loudly, slowing progress! (-5% success chance)", "chance_penalty": 0.05},
            {"text": "⚠️ Had to bribe the prison geologist.", "currency_penalty": 300}
        ]
    },
    {
        "name": "Prison Riot",
        "attempt_text": "🚨 {user} starts a prison riot as a distraction...",
        "success_text": "🚨 In the chaos of the riot, {user} slips away unnoticed! Freedom at last!",
        "fail_text": "🚨 The riot was quickly contained. {user} was identified as the instigator and sent to solitary.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ Other prisoners join your cause! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ You found a guard's keycard! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ You looted the commissary during the chaos!", "currency_bonus": 300},
            {"text": "⭐ The prison's WiFi went down - guards are distracted! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ Someone released all the therapy dogs! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Found the warden's secret stash!", "currency_bonus": 500},
            {"text": "⚠️ The guards were prepared! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ Security cameras caught your plan! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ You had to bribe another prisoner to keep quiet.", "currency_penalty": 250},
            {"text": "⚠️ The SWAT team arrived! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ Your riot chant was too cringe! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to replace broken furniture.", "currency_penalty": 350}
        ]
    },
    {
        "name": "Guard Disguise",
        "attempt_text": "🕶 {user} puts on a stolen guard uniform...",
        "success_text": "🕶 Nobody questioned {user} as they walked right out the front door! The perfect disguise!",
        "fail_text": "🕶 The uniform was from last season's collection. {user} was spotted immediately by the fashion-conscious guards.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ Shift change creates confusion! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ You memorized the guard patterns! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ You found {currency} in the uniform pocket!", "currency_bonus": 250},
            {"text": "⭐ It's casual Friday - perfect timing! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ Found the guard's secret handshake manual! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Discovered the guard's poker winnings!", "currency_bonus": 450},
            {"text": "⚠️ Your shoes don't match the uniform! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ A guard recognizes you! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ You had to pay another inmate for the uniform.", "currency_penalty": 200},
            {"text": "⚠️ Your badge is upside down! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ You forgot the guard's catchphrase! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to buy authentic guard boots.", "currency_penalty": 275}
        ]
    },
    {
        "name": "Food Cart Escape",
        "attempt_text": "🍽️ {user} attempts to hide in the kitchen's food delivery cart...",
        "success_text": "🍽️ Buried under a mountain of mystery meat, {user} was wheeled right out to the delivery truck. The meat was terrible, but freedom tastes sweet!",
        "fail_text": "🍽️ Return to sender! {user} forgot to put enough stamps on themselves. The postal service has strict policies about shipping prisoners.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ It's holiday rush season! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ You found a perfect-sized box! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ You discovered undelivered {currency} money orders!", "currency_bonus": 275},
            {"text": "⭐ Health inspector visit - everyone's distracted! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ The chef is having a meltdown! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Found tips from the cooking class!", "currency_bonus": 350},
            {"text": "⚠️ Package inspection in progress! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ The box is too heavy! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to pay for express shipping.", "currency_penalty": 225},
            {"text": "⚠️ Someone ordered a surprise inspection! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ The food cart has a squeaky wheel! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to bribe the kitchen staff.", "currency_penalty": 300}
        ]
    },
    {
        "name": "Laundry Escape",
        "attempt_text": "👕 {user} tries to sneak out with the laundry truck...",
        "success_text": "👕 Folded between fresh sheets, {user} enjoyed a comfortable ride to freedom! The prison's 1-star laundry service just lost its best customer.",
        "fail_text": "👕 {user} was found when they couldn't hold in a sneeze. Turns out hiding in old pepper wasn't the best idea.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ The laundry is extra fluffy today! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ It's extra stinky today - guards won't look! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ You found valuables in the trash!", "currency_bonus": 225},
            {"text": "⭐ Static electricity makes you invisible! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ Found a lucky sock! (+5% success chance)", "chance_bonus": 0.05},
            {"text": "⭐ Discovered money in the dryer!", "currency_bonus": 275},
            {"text": "⚠️ Guard dog inspection day! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ The dumpster has holes in it! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to buy air fresheners.", "currency_penalty": 175},
            {"text": "⚠️ The washing machine is leaking! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ You're allergic to the detergent! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to pay for premium fabric softener.", "currency_penalty": 225}
        ]
    },
    {
        "name": "Visitor Swap",
        "attempt_text": "🎭 {user} attempts to switch places with a visitor...",
        "success_text": "🎭 The perfect crime! {user}'s identical twin cousin twice removed walked in, and {user} walked out. Family reunions will be awkward though.",
        "fail_text": "🎭 Turns out your 'identical' cousin was actually your complete opposite. The guards couldn't stop laughing as they dragged you back.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ Your cousin is a master of disguise! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ The visiting room is extra crowded! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Your cousin slipped you some cash!", "currency_bonus": 300},
            {"text": "⭐ It's twins day at the prison! (+25% success chance)", "chance_bonus": 0.25},
            {"text": "⭐ Your makeup skills improved! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Found money in the visitor's locker!", "currency_bonus": 400},
            {"text": "⚠️ The guard is doing double ID checks! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ Your cousin has a distinctive walk! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to buy matching clothes.", "currency_penalty": 250},
            {"text": "⚠️ New biometric scanners installed! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ You forgot your visitor's backstory! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to buy premium disguise materials.", "currency_penalty": 350}
        ]
    },
    {
        "name": "Helicopter Rescue",
        "attempt_text": "🚁 {user} signals their accomplice in a helicopter...",
        "success_text": "🚁 Action movie style! {user} grabbed the rope ladder and soared away while the guards stood in awe. Someone's been watching too many movies!",
        "fail_text": "🚁 Plot twist: It was actually a police helicopter. {user} just got featured on 'World's Most Embarrassing Prison Breaks'.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ Your pilot is an ex-stunt double! (+25% success chance)", "chance_bonus": 0.25},
            {"text": "⭐ Perfect weather conditions! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ You grabbed the prison's petty cash box!", "currency_bonus": 400},
            {"text": "⭐ The guards are watching an air show! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ Your pilot has gaming experience! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Found the warden's emergency fund!", "currency_bonus": 600},
            {"text": "⚠️ Anti-aircraft spotlight activated! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ High winds today! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ Had to pay the pilot's fuel costs.", "currency_penalty": 200},
            {"text": "⚠️ The prison installed anti-air defenses! (-30% success chance)", "chance_penalty": 0.30},
            {"text": "⚠️ Motion sickness kicks in! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to pay for helicopter maintenance.", "currency_penalty": 450}
        ]
    },
    {
        "name": "Drama Club Escape",
        "attempt_text": "🎭 {user} uses the prison drama club performance as cover...",
        "success_text": "🎭 Oscar-worthy performance! {user} played their role so well, they convinced everyone they were just an actor playing a prisoner. The reviews were stellar!",
        "fail_text": "🎭 {user} forgot their lines and improvised a real escape attempt. The audience thought it was part of the show and gave a standing ovation as they were dragged back.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ You're starring in 'The Great Escape'! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ The audience is completely captivated! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ You found money in the prop cash box!", "currency_bonus": 250},
            {"text": "⭐ Broadway scout in the audience! (+25% success chance)", "chance_bonus": 0.25},
            {"text": "⭐ The spotlight malfunctioned! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ Won the drama competition prize!", "currency_bonus": 450},
            {"text": "⚠️ The guard is a theatre critic! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ Stage fright kicks in! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to bribe the stage manager.", "currency_penalty": 200},
            {"text": "⚠️ Method actor guard on duty! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ You're in the wrong costume! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to pay for premium props.", "currency_penalty": 300}
        ]
    },
    {
        "name": "Mail Room Mixup",
        "attempt_text": "📦 {user} tries to mail themselves to freedom...",
        "success_text": "📦 Special delivery! {user} was successfully shipped to freedom with Prime shipping. The 1-star review for 'uncomfortable packaging' was worth it!",
        "fail_text": "📦 Return to sender! {user} forgot to put enough stamps on themselves. The postal service has strict policies about shipping prisoners.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ It's holiday rush season! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ You found a perfect-sized box! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ You discovered undelivered {currency} money orders!", "currency_bonus": 275},
            {"text": "⭐ New temp worker doesn't check labels! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ Found bubble wrap to hide in! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Discovered a misplaced Amazon package!", "currency_bonus": 350},
            {"text": "⚠️ Package inspection in progress! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ The box is too heavy! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to pay for express shipping.", "currency_penalty": 225},
            {"text": "⚠️ X-ray machine just got upgraded! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ You're not Prime eligible! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to pay for overnight shipping.", "currency_penalty": 400}
        ]
    },
    {
        "name": "Trash Compactor Gambit",
        "attempt_text": "🗑️ {user} attempts to sneak out with the garbage...",
        "success_text": "🗑️ One man's trash is another man's ticket to freedom! {user} made it out smelling like week-old fish sticks, but at least they're free!",
        "fail_text": "🗑️ {user} was found when they couldn't hold in a sneeze. Turns out hiding in old pepper wasn't the best idea.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ The garbage truck driver is napping! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ It's extra stinky today - guards won't look! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ You found valuables in the trash!", "currency_bonus": 225},
            {"text": "⭐ It's recycling awareness day! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ Found a hazmat suit in the trash! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ Discovered the janitor's secret savings!", "currency_bonus": 375},
            {"text": "⚠️ Guard dog inspection day! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ The dumpster has holes in it! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to buy air fresheners.", "currency_penalty": 175},
            {"text": "⚠️ New waste management protocols! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ The compactor is malfunctioning! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ Had to bribe the garbage collector.", "currency_penalty": 325}
        ]
    },
    {
        "name": "Prison Band jailbreak",
        "attempt_text": "🎸 {user} hides inside the prison band's bass drum...",
        "success_text": "🎸 {user} rode the rhythm all the way to freedom! The band's encore performance was suspiciously lighter.",
        "fail_text": "🎸 {user} ruined the big finale by sneezing during the drum solo. The critics were not impressed.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ The band is playing extra loud! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ You're in the back row! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ You found {currency} from the performance!", "currency_bonus": 200},
            {"text": "⭐ Famous musician visiting today! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ The acoustics are perfect! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Found the band's tip jar!", "currency_bonus": 325},
            {"text": "⚠️ The drum has a hole! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Guard requests a song! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to bribe the drummer.", "currency_penalty": 175},
            {"text": "⚠️ The warden is a music critic! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ You're rhythmically challenged! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to pay for instrument repairs.", "currency_penalty": 275}
        ]
    },
    {
        "name": "Prison Olympics",
        "attempt_text": "🏃 {user} enters the prison's annual sports competition...",
        "success_text": "🏃 {user} took gold in the 100-meter dash... right past the gates! A record-breaking performance!",
        "fail_text": "🏃 {user} got disqualified for running in the wrong direction. The judges were not impressed.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ You're in peak condition! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ The crowd is cheering for you! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ You won the {currency} prize!", "currency_bonus": 350},
            {"text": "⭐ Olympic scout in attendance! (+25% success chance)", "chance_bonus": 0.25},
            {"text": "⭐ Performance enhancing snacks! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Found the betting pool money!", "currency_bonus": 500},
            {"text": "⚠️ Professional referee watching! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ You pulled a muscle! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Entry fee and equipment costs.", "currency_penalty": 275},
            {"text": "⚠️ Drug testing in progress! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ Forgot to stretch! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to buy premium running shoes.", "currency_penalty": 350}
        ]
    },
    {
        "name": "Prison Art Show",
        "attempt_text": "🎨 {user} plans to escape during the prison art exhibition...",
        "success_text": "🎨 {user} posed as a modern art installation and was shipped to a museum! Critics called it 'A moving piece about freedom.'",
        "fail_text": "🎨 {user}'s 'Statue of Liberty' pose wasn't convincing enough. The art critics gave it zero stars.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ Your art got first place! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ The gallery is packed! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Someone bought your artwork!", "currency_bonus": 275},
            {"text": "⭐ Famous art collector visiting! (+25% success chance)", "chance_bonus": 0.25},
            {"text": "⭐ Abstract art exhibition - perfect cover! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ Won the People's Choice Award!", "currency_bonus": 450},
            {"text": "⚠️ The curator is suspicious! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Paint is still wet! (-10% success chance)", "chance_penalty": 0.10},
            {"text": "⚠️ Had to buy art supplies.", "currency_penalty": 225},
            {"text": "⚠️ Art authenticator on site! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ Your masterpiece is smudged! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to buy premium art materials.", "currency_penalty": 375}
        ]
    },
    {
        "name": "Prison Cooking Show",
        "attempt_text": "👨‍🍳 {user} participates in the prison's cooking competition...",
        "success_text": "👨‍🍳 {user}'s soufflé was so good, they were immediately hired by a 5-star restaurant... on the outside!",
        "fail_text": "👨‍🍳 {user}'s escape plan fell flat like their failed soufflé. Back to the kitchen duty.",
        "base_chance": 0.35,
        "events": [
            {"text": "⭐ Your dish impressed Gordon Ramsay! (+20% success chance)", "chance_bonus": 0.20},
            {"text": "⭐ Kitchen is in chaos! (+15% success chance)", "chance_bonus": 0.15},
            {"text": "⭐ Won the {currency} prize!", "currency_bonus": 300},
            {"text": "⭐ Celebrity chef guest judge! (+25% success chance)", "chance_bonus": 0.25},
            {"text": "⭐ Found the secret recipe book! (+10% success chance)", "chance_bonus": 0.10},
            {"text": "⭐ Catering contract opportunity!", "currency_bonus": 550},
            {"text": "⚠️ Food critic is watching! (-20% success chance)", "chance_penalty": 0.20},
            {"text": "⚠️ Kitchen fire alert! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to buy premium ingredients.", "currency_penalty": 250},
            {"text": "⚠️ Health inspector surprise visit! (-25% success chance)", "chance_penalty": 0.25},
            {"text": "⚠️ Your sauce is too bland! (-15% success chance)", "chance_penalty": 0.15},
            {"text": "⚠️ Had to buy truffle ingredients.", "currency_penalty": 400}
        ]
    }
]
