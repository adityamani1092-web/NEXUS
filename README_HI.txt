NEXUS PREMIUM BOT — HELP STYLE PACKAGE

Files: bot.py, db.py, requirements.txt, help_banner.jpg, nexus_banner.png
Keep all files in the same folder. Keep your existing .env file private.

Setup:
1. Install Python 3.10+.
2. Open terminal/CMD in this folder.
3. Run: python -m pip install -r requirements.txt
4. Ensure .env contains BOT_TOKEN and OWNER_ID (plus any existing dashboard settings).
5. Run: python bot.py

Private /start shows the NEXUS banner and buttons: Add to Group, Help & Commands, Ping, Games.
/help shows the stylish category help menu. Games button opens a games submenu.
For group moderation, add the bot to the group and grant only the permissions needed.
Users must press /start in DM before the bot can send them a DM broadcast. Broadcast is owner-only.

Safety: Never share your bot token or .env. Code syntax was checked; live Telegram behavior has not been tested.
