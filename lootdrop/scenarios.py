"""
Scenarios for the LootDrop cog
Each scenario has:
- start: The initial scenario message
- good: Good outcome message template
- bad: Bad outcome message template
- button_text: Text to show on the claim button
- button_emoji: Emoji to show on the claim button

The {user} placeholder will be replaced with the user's mention in outcomes
The {amount} placeholder will be replaced with the currency amount
The {currency} placeholder will be replaced with the guild's currency name
"""
from typing import List, Dict, TypedDict


class Scenario(TypedDict):
    start: str  # The initial scenario message
    good: str   # Good outcome message template
    bad: str    # Bad outcome message template
    button_text: str  # Text to show on claim button
    button_emoji: str  # Emoji to show on claim button


SCENARIOS: List[Scenario] = [
    {
        "start": "💾 A dusty USB drive labeled 'Top Secret Mod Notes' lies forgotten...",
        "good": "{user} returns the drive to the mods and gets {amount} {currency} for their honesty!",
        "bad": "The drive contained a virus! {user} pays {amount} {currency} to the server tech support role.",
        "button_text": "Check Drive",
        "button_emoji": "💾"
    },
    {
        "start": "🤖 A wild `LootBot` appears in the channel, sparkling strangely...",
        "good": "{user} interacts with the bot and it glitches, dropping {amount} {currency}!",
        "bad": "The bot was a mimic! It bites {user} and steals {amount} {currency}!",
        "button_text": "Interact",
        "button_emoji": "🤖"
    },
    {
        "start": "📥 A DM pops up from a new user: 'Click here for free {currency}!!1!'...",
        "good": "{user} reports the scammer and the server owner rewards them with {amount} {currency}!",
        "bad": "It was a phishing link! {user} loses {amount} {currency} fixing their account!",
        "button_text": "Check Link",
        "button_emoji": "🔗"
    },
    {
        "start": "🌟 A Discord Nitro link appears in the channel...",
        "good": "{user} claims the Nitro and finds a bonus {amount} {currency}!",
        "bad": "It was a fake link! {user} feels the sting of disappointment in themselves and was hacked, losing {amount} {currency}.",
        "button_text": "Claim Nitro",
        "button_emoji": "✨"
    },
    {
        "start": "🎤 Someone started Karaoke night in the VC, but the next singer is shy...",
        "good": "{user} belts out a banger! The crowd showers them with {amount} {currency}!",
        "bad": "{user}'s mic feedback breaks the bot! They pay {amount} {currency} for repairs!",
        "button_text": "Grab Mic",
        "button_emoji": "🎤"
    },
    {
        "start": "💰 A suspicious looking wallet lies on the ground...",
        "good": "{user} steals the wallet full of {amount} {currency} and runs away!",
        "bad": "{user} was caught by the police! {amount} {currency} fine!",
        "button_text": "Pick up wallet",
        "button_emoji": "👛"
    },
    {
        "start": "✨ A mysterious chest materializes out of thin air...",
        "good": "{user} opens the chest and finds {amount} {currency} worth of treasure!",
        "bad": "The chest was cursed! {user} pays {amount} {currency} to break free!",
        "button_text": "Open chest",
        "button_emoji": "🗝️"
    },
    {
        "start": "🎲 A sketchy merchant appears with a game of chance...",
        "good": "{user} wins the game and receives {amount} {currency}!",
        "bad": "{user} loses the game and pays {amount} {currency} to the merchant!",
        "button_text": "Play game",
        "button_emoji": "🎲"
    },
    {
        "start": "🎭 A street performer seeks a volunteer from the crowd...",
        "good": "The crowd loves {user}'s performance! They earn {amount} {currency} in tips!",
        "bad": "{user} accidentally breaks the props! They pay {amount} {currency} in damages!",
        "button_text": "Volunteer",
        "button_emoji": "🎭"
    },
    {
        "start": "📦 An unmarked package sits mysteriously on the doorstep...",
        "good": "{user} opens a surprise gift containing {amount} {currency}!",
        "bad": "It's a prank package! {user} spends {amount} {currency} cleaning up the mess!",
        "button_text": "Open package",
        "button_emoji": "📦"
    },
    {
        "start": "🎪 An enticing carnival game stand appears...",
        "good": "{user} wins the jackpot! {amount} {currency} richer!",
        "bad": "The game was rigged by a rival server! {user} loses {amount} {currency}!",
        "button_text": "Try your luck",
        "button_emoji": "🎯"
    },
    {
        "start": "🎮 A vintage arcade cabinet flickers to life...",
        "good": "{user} finds {amount} {currency} worth of tokens inside!",
        "bad": "The machine eats {user}'s {currency}! {amount} lost to the void!",
        "button_text": "Insert coin",
        "button_emoji": "🕹️"
    },
    {
        "start": "🎣 A golden fishing rod floats in a nearby pond...",
        "good": "{user} catches a rare fish worth {amount} {currency}!",
        "bad": "{user} falls in and loses {amount} {currency} worth of electronics!",
        "button_text": "Cast line",
        "button_emoji": "🎣"
    },
    {
        "start": "🎨 A street artist offers to paint your portrait...",
        "good": "The painting sells for {amount} {currency}! {user} gets the profits!",
        "bad": "The paint was permanent! {user} pays {amount} {currency} for removal!",
        "button_text": "Pose",
        "button_emoji": "🎨"
    },
    {
        "start": "🎵 A ghostly music box plays a haunting melody...",
        "good": "The ghost rewards {user} with {amount} {currency} for listening!",
        "bad": "The cursed tune costs {user} {amount} {currency} to forget!",
        "button_text": "Listen closer",
        "button_emoji": "👻"
    },
    {
        "start": "🌋 A dormant volcano rumbles ominously...",
        "good": "{user} discovers ancient treasure worth {amount} {currency}!",
        "bad": "The eruption destroys {user}'s belongings! {amount} {currency} in damages!",
        "button_text": "Investigate",
        "button_emoji": "🌋"
    },
    {
        "start": "🎪 A time traveler's briefcase appears in a flash of light...",
        "good": "{user} finds futuristic currency worth {amount} {currency}!",
        "bad": "Temporal police fine {user} {amount} {currency} for interference!",
        "button_text": "Open briefcase",
        "button_emoji": "⌛"
    },
    {
        "start": "🎰 A malfunctioning vending machine sparks and whirs...",
        "good": "The machine dispenses {amount} {currency} to {user}!",
        "bad": "The machine swallows {user}'s card and charges {amount} {currency}!",
        "button_text": "Press buttons",
        "button_emoji": "🎰"
    },
    {
        "start": "🎭 An ancient mask whispers secrets of power...",
        "good": "{user} learns wisdom worth {amount} {currency}!",
        "bad": "The mask possesses {user}! Exorcism costs {amount} {currency}!",
        "button_text": "Wear mask",
        "button_emoji": "👺"
    },
    {
        "start": "🎪 A dimensional rift tears open reality...",
        "good": "Alternate {user} sends {amount} {currency} through the portal!",
        "bad": "Evil {user} steals {amount} {currency} and escapes!",
        "button_text": "Enter portal",
        "button_emoji": "🌀"
    },
    {
        "start": "🎨 A blank canvas radiates mysterious energy...",
        "good": "{user}'s artwork magically comes alive, worth {amount} {currency}!",
        "bad": "The painting traps {user}! Rescue costs {amount} {currency}!",
        "button_text": "Start painting",
        "button_emoji": "🖌️"
    },
    {
        "start": "🎭 A magical mirror shows your reflection...",
        "good": "{user}'s reflection hands over {amount} {currency}!",
        "bad": "The mirror traps {user}'s shadow! Ransom costs {amount} {currency}!",
        "button_text": "Touch mirror",
        "button_emoji": "🎭"
    },
    {
        "start": "🎪 A cosmic vending machine descends from space...",
        "good": "{user} receives alien technology worth {amount} {currency}!",
        "bad": "The machine abducts {user}'s {currency}! {amount} lost to space!",
        "button_text": "Insert {currency}",
        "button_emoji": "👽"
    },
    {
        "start": "🎲 A mysterious game board draws you in...",
        "good": "{user} wins the cosmic game and {amount} {currency}!",
        "bad": "Jumanji-style chaos costs {user} {amount} {currency} to fix!",
        "button_text": "Roll dice",
        "button_emoji": "🎲"
    },
    {
        "start": "🌈 A unicorn offers to grant a wish...",
        "good": "{user}'s pure heart earns {amount} {currency}!",
        "bad": "The unicorn judges {user} unworthy! Fine of {amount} {currency}!",
        "button_text": "Make wish",
        "button_emoji": "🦄"
    },
    {
        "start": "🎭 A sentient shadow offers a deal...",
        "good": "{user} outsmarts the shadow and gains {amount} {currency}!",
        "bad": "The shadow steals {user}'s luck! {amount} {currency} to recover!",
        "button_text": "Make deal",
        "button_emoji": "🌑"
    },
    {
        "start": "🍦 An ice cream truck is playing its tune late at night...",
        "good": "{user} gets free unlimited ice cream and {amount} {currency}!",
        "bad": "It was a trap! {user} pays {amount} {currency} for melted ice cream!",
        "button_text": "Chase truck",
        "button_emoji": "🍦"
    },
    {
        "start": "🎰 A casino slot machine is spinning on its own...",
        "good": "{user} hits the jackpot! {amount} {currency} richer!",
        "bad": "Security catches {user} and fines them {amount} {currency}!",
        "button_text": "Pull lever",
        "button_emoji": "🎰"
    },
    {
        "start": "💎 The jewelry store's alarm system appears to be malfunctioning...",
        "good": "{user} finds a lost diamond worth {amount} {currency}!",
        "bad": "The alarm was fake! {user} pays {amount} {currency} in fines!",
        "button_text": "Investigate",
        "button_emoji": "💎"
    },
    {
        "start": "🏦 The bank's vault door has opened by itself...",
        "good": "{user} finds unclaimed {currency} worth {amount}!",
        "bad": "It was a security test! {user} pays {amount} {currency} in fines!",
        "button_text": "Peek inside",
        "button_emoji": "🏦"
    },
    {
        "start": "🚗 A luxury car is parked nearby with keys in the ignition...",
        "good": "{user} returns the car and gets {amount} {currency} reward!",
        "bad": "The owner catches {user}! {amount} {currency} fine!",
        "button_text": "Check car",
        "button_emoji": "🚗"
    },
    {
        "start": "🎭 A masquerade party is happening at the mansion...",
        "good": "{user} wins best costume and {amount} {currency}!",
        "bad": "The mask falls off! {user} pays {amount} {currency} to escape!",
        "button_text": "Crash party",
        "button_emoji": "🎭"
    },
    {
        "start": "🖼️ The art gallery's security cameras have stopped working...",
        "good": "{user} discovers a forgotten masterpiece worth {amount} {currency}!",
        "bad": "The art was fake! {user} loses {amount} {currency}!",
        "button_text": "Browse art",
        "button_emoji": "🖼️"
    },
    {
        "start": "🎪 Music is coming from the circus tent after hours...",
        "good": "{user} finds {amount} {currency} in lost tickets!",
        "bad": "The clowns catch {user}! {amount} {currency} to join the show!",
        "button_text": "Sneak in",
        "button_emoji": "🎪"
    },
    {
        "start": "🏰 The castle's treasure room door is standing wide open...",
        "good": "{user} finds ancient coins worth {amount} {currency}!",
        "bad": "The knights catch {user}! {amount} {currency} fine!",
        "button_text": "Enter room",
        "button_emoji": "🏰"
    },
    {
        "start": "🎵 A street musician has left their hat full of coins...",
        "good": "{user} performs and earns {amount} {currency} in tips!",
        "bad": "The crowd boos! {user} pays {amount} {currency} to leave!",
        "button_text": "Join music",
        "button_emoji": "🎵"
    },
    {
        "start": "🎮 The arcade's machines are running without power...",
        "good": "{user} rescues {amount} {currency} worth of tokens!",
        "bad": "The games malfunction! {user} pays {amount} {currency} in damages!",
        "button_text": "Check games",
        "button_emoji": "🎮"
    },
    {
        "start": "🚁 A helicopter is sitting idle with keys in the cockpit...",
        "good": "{user} takes a joyride and finds {amount} {currency}!",
        "bad": "Crash landing! {user} pays {amount} {currency} in repairs!",
        "button_text": "Start heli",
        "button_emoji": "🚁"
    },
    {
        "start": "🎨 The museum is unveiling a mysterious new exhibit...",
        "good": "{user} discovers a lost artwork worth {amount} {currency}!",
        "bad": "The curator catches {user}! Fine of {amount} {currency}!",
        "button_text": "Preview art",
        "button_emoji": "🎨"
    },
    {
        "start": "🎩 A magician's hat is sitting unattended on stage...",
        "good": "{user} pulls out {amount} {currency} worth of magic!",
        "bad": "The rabbit bites! {user} pays {amount} {currency} in damages!",
        "button_text": "Reach in",
        "button_emoji": "🎩"
    },
    {
        "start": "🌴 A private beach at the resort is completely empty...",
        "good": "{user} finds buried treasure worth {amount} {currency}!",
        "bad": "Security escorts {user} out! {amount} {currency} fine!",
        "button_text": "Explore beach",
        "button_emoji": "🌴"
    },
    {
        "start": "🎣 Someone is hosting a fishing event...",
        "good": "{user} catches the legendary server fish, worth {amount} {currency}!",
        "bad": "{user} snags their line on the bot's code, costing {amount} {currency} to untangle!",
        "button_text": "Cast Line",
        "button_emoji": "🎣"
    },
    {
        "start": "👻 A ghostly ping notification sound echoes, but there's no new message...",
        "good": "It's a ghost notification! {user} finds the phantom {amount} {currency} left behind!",
        "bad": "The sound haunts {user}! They pay {amount} {currency} for premium sound packs to forget it!",
        "button_text": "Investigate Ping",
        "button_emoji": "👻"
    },
    {
        "start": "📜 A new quest pops up on the server notice board! 'Defeat 10 Spam Bots'...",
        "good": "{user} completes the quest and earns {amount} {currency} from the Quest Master role!",
        "bad": "The spam bots overwhelmed {user}! They pay {amount} {currency} for anti-spam protection.",
        "button_text": "Accept Quest",
        "button_emoji": "📜"
    },
    {
        "start": "🐲 A wild Server Boss (a glitchy bot?) appears, dropping loot!",
        "good": "{user} lands the killing blow and gets the Legendary Loot Drop worth {amount} {currency}!",
        "bad": "The Boss's AOE attack hits {user}! Repair costs are {amount} {currency}!",
        "button_text": "Attack Boss",
        "button_emoji": "⚔️"
    },
    {
        "start": "🗺️ An unexplored, dusty channel is discovered...",
        "good": "{user} finds ancient server lore worth {amount} {currency} to the historians!",
        "bad": "The channel is haunted by ghost pings! {user} pays {amount} {currency} for mental recovery.",
        "button_text": "Explore Channel",
        "button_emoji": "🗺️"
    },
    {
        "start": "🛡️ The server is being DDoSed!",
        "good": "{user}'s quick thinking helps repel the attack! Rewarded with {amount} {currency} for valor!",
        "bad": "{user}'s connection drops during the fight! Reconnecting costs {amount} {currency}.",
        "button_text": "Defend Server",
        "button_emoji": "🛡️"
    },
    {
        "start": "⚙️ A small, whirring mechanical creature scurries by, trailing sparks...",
        "good": "{user} catches the creature and finds it carries {amount} {currency}!",
        "bad": "The creature unleashes an electric shock! {user} pays {amount} {currency} for repairs.",
        "button_text": "Catch It",
        "button_emoji": "⚙️"
    },
    {
        "start": "📜 A tattered scroll lies on the path, sealed with an unknown sigil...",
        "good": "{user} breaks the seal and finds a treasure map leading to {amount} {currency}!",
        "bad": "The scroll releases a minor curse! {user} pays {amount} {currency} to a local healer.",
        "button_text": "Read Scroll",
        "button_emoji": "📜"
    },
    {
        "start": "☄️ A fragment of a falling star lands nearby, glowing softly...",
        "good": "{user} carefully picks up the star fragment, finding it's worth {amount} {currency}!",
        "bad": "The fragment burns {user}'s hand! Ointment costs {amount} {currency}.",
        "button_text": "Touch Fragment",
        "button_emoji": "☄️"
    },
    {
        "start": "👻 A faint, chilling whisper seems to echo from the shadows...",
        "good": "{user} follows the whisper and finds {amount} {currency} hidden by a restless spirit!",
        "bad": "The whisper drains {user}'s energy! A potion costs {amount} {currency}.",
        "button_text": "Follow Whisper",
        "button_emoji": "👻"
    },
    {
        "start": "📜 A bounty is posted... 'Clear out the mischievous imps plaguing the area'",
        "good": "{user} bravely defeats the imps and collects the {amount} {currency} reward!",
        "bad": "The imps played tricks on {user}, stealing {amount} {currency}!",
        "button_text": "Accept Bounty",
        "button_emoji": "📜"
    },
    {
        "start": "🗿 A hulking golem, crafted from stone and metal, blocks the path!",
        "good": "{user} finds the golem's weak spot and disables it, finding {amount} {currency} inside!",
        "bad": "The golem smashes {user}'s backpack! Replacing gear costs {amount} {currency}.",
        "button_text": "Fight Golem",
        "button_emoji": "🗿"
    },
    {
        "start": "⛈️ A sudden, unnatural storm gathers overhead...",
        "good": "{user} finds shelter and discovers {amount} {currency} left by another traveler!",
        "bad": "A lightning strike nearby scares {user}, causing them to drop {amount} {currency}!",
        "button_text": "Seek Shelter",
        "button_emoji": "⛈️"
    }
]
