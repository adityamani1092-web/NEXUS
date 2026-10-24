NEXUS BOT — ROSE-INSPIRED HELP + VISUAL GAME CARDS

This build expands the DM /help center with a Rose-inspired category menu and adds image-based question cards for the existing mini-games. It is not a clone of every Rose Bot feature: the help menu lists the commands implemented in this codebase only.

FILES
- bot.py: Telegram bot, categorized DM help, group management, filters, moderation, couple card, image-generation command and visual puzzle cards
- db.py: SQLite database functions
- requirements.txt: Python dependencies
- .env.example: safe environment template (no real secrets)
- nexus_banner.png / help_banner.jpg: bot and help artwork
- new_couple_image.jpg / auto_couple_image.jpg: couple card assets

RENDER SETUP
1. Upload these files to the root of the GitHub repository.
2. In Render, set Build Command: pip install -r requirements.txt
3. Set Start Command: python bot.py
4. In Render > Environment, add values from .env.example as separate variables. Never upload a real .env or secrets to public GitHub.
5. Ensure bot is added to the group. Give it administrator permissions needed for ban/mute/lock and message/photo permissions.

ENVIRONMENT VARIABLES
BOT_TOKEN=your_telegram_bot_token
OWNER_ID=your_numeric_telegram_user_id
WEB_SECRET=generate_a_long_random_secret
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=use_a_strong_unique_password
OPENAI_API_KEY=your_openai_api_key
IMAGE_MODEL=gpt-image-2.5-flare
IMAGE_COOLDOWN_SECONDS=30
IMAGE_DAILY_LIMIT=10
IMAGE_QUALITY=medium
PORT=8080

DM HELP MENU
- /start opens the main menu
- Press HELP & COMMANDS, then Group Management, Moderation, Filters, Games, Tools & AI, Broadcast or other categories.
- /help opens the same categorized help center.

GROUP COMMANDS (implemented in this build)
- Moderation: /ban, /unban, /mute, /unmute, /lock, /unlock, /lockinfo, /antispam, /free, /unfree, /approve, /decline
- Filters: /filter, /filters, /stop
- User tools: /id, /info, /history, /adminlist, /report
- AI images: /imagine <prompt>, /image <prompt>
- Social/ranking: /couple, /points, /top, /auratop, /worldtop, /worldauratop, /giveaura, /protect, /rob
- Games: /hidden, /scramble, /anagram, /wordle, /hangman, /wordchain, /guessnumber, /fasttype, /truefalse, /trivia, /riddle, /emojiquiz, /mathquiz, /puzzlehelp

FILTER PERMISSIONS
The configured bot owner or a Telegram administrator of that group can create/list/remove filters in that group. Filters are group-scoped. The bot should have permission to send messages; delete permission is optional for filter replies.

AURA / RANKING
- Positive word detected in a group message: +50 Aura per positive word; negative word: -50 per negative word.
- Maximum sentiment change per message is +/-500 Aura, and sentiment rewards have a 60-second cooldown per user per group to reduce spam/farming.
- /giveaura amount works by replying to a member; /giveaura @username amount also works if the bot has seen that user. The sender must have enough Aura.
- /protect 1d costs 500 coins; /protect 2d costs 1000 coins. Protection blocks Aura losses for the selected time; it does not automatically remove 500 Aura.
- /auratop and /top show this group's rankings. /worldauratop and /worldtop aggregate saved scores across groups where Nexus has recorded the same users. This is a worldwide-style leaderboard, not a list of every Telegram user.

VISUAL GAMES
Puzzle commands now send a generated visual question card with the game title and prompt. Answer in the same group; first correct answer wins and earns +3000 coins / +50 Aura; incorrect guesses currently lose 60 Aura. Players must press /start in bot DM first.

AI IMAGE GENERATION
Use /imagine a futuristic city at night or /image a cute anime robot. OpenAI API use is paid and needs a valid API key, billing, and model access. Check current official pricing before enabling for a busy group. Do not post API keys in chat or commit them to GitHub.

LIMITATIONS / VERIFICATION
- This package is syntax-checked and ZIP-integrity-checked, and the local game-card rendering helper is smoke-tested. It has not been live-tested against the user's Telegram bot token, Render service, or OpenAI API key.
- Telegram cannot provide complete historical usernames or messages that the bot never observed.
- Some advanced Rose features (such as federations, full CAPTCHA flows, topic management, full note system, purge tooling, and every Rose configuration) are not implemented in this build and are not represented as working commands in the help menu.
- Sentiment Aura cooldowns are stored in SQLite; image cooldown/daily counters are in-memory and reset when the process restarts. Global rankings only include scores recorded in this bot's database.

ANTI-LINK & MEMBER APPROVAL (NEW)
---------------------------------
Group admins can configure:
- /antilink on   : delete URLs from unapproved members' group messages
- /antilink off  : disable the link filter
- /linkmode warn : warn on each link violation (default)
- /linkmode mute : mute after the configured warning threshold
- /linkwarn 3    : number of link violations before a mute (1-10)
- /linkmute 10   : mute duration in minutes (1-10080)
- Reply to a member with /approve, or use /approve USER_ID /approve @username,
  to allow that member to post links without anti-link moderation.
- /unapprove with a reply, user ID, or known @username removes that exception.

Important Telegram limitation: the official Telegram Bot API does not expose a
member's profile bio to bots. Therefore this anti-link feature checks links in
messages/captions posted in the group, not links stored in a profile bio. For
message deletion and timed mute, promote Nexus to admin and grant Delete Messages
and Restrict Members permissions. Username resolution requires Nexus to have
seen the user before.

The /start screen already includes the banner image and an ADD TO GROUP button.

AUTO QUIZ (NEW)
- Bot known groups mein lagbhag har 2 ghante ek naya visual quiz/photo card post karta hai.
- Question bank mein general knowledge, true/false aur riddles hain; same group mein pichhla question back-to-back repeat nahi hota.
- Group mein pehla correct answer dene wale ko configured game reward (+3000 coins, +50 Aura) milta hai.
- Timing change karne ke liye environment variable AUTO_QUIZ_INTERVAL_HOURS set karein (default 2).
- Bot ko group mein send messages aur send photos permission chahiye. Group ko bot ke database mein known hona chahiye; bot ko group mein add karke ek message bhejein.
