ROSEBOT UPDATED - SETUP (HINGLISH)

1. Python 3.11+ install karein.
2. Folder ke andar terminal/CMD kholen.
3. Install: pip install -r requirements.txt
4. .env.example ko copy karke .env naam dein.
5. .env mein BOT_TOKEN, OWNER_ID, WEB_SECRET aur DASHBOARD_PASSWORD set karein.
6. Start: python bot.py
7. Telegram par bot ko /start karein, group mein add karein aur admin banayein.
8. Group filter ke liye BotFather mein privacy mode disable karna pad sakta hai.
9. Ek hi bot process chalayein. Cloud hosting par persistent disk ke liye DB_PATH set karein.

MAIN COMMANDS
/start /help /ping /id /info
/ban @username | /unban USER_ID | /mute @username 30 | /unmute USER_ID
/filter keyword response | reply to sticker/photo with /filter response
/filters
/points /top /auratop /protect 1d /protect 2d
/giveaura @username amount (sender ke paas itna Aura hona chahiye)
/rob @username [amount] (55% chance; failed rob par transfer nahi hota)
/approve USER_ID|@username /decline USER_ID|@username (pending join request only; reply/username works when user is known)
/antispam on|off|status (flood and repeated-message protection; ON by default)
/history USER_ID|@username (saved name history)
/translate hi|en|off (group automatic translation)
/broadcast message (owner: DM + known groups)
/broadcast_at YYYY-MM-DD HH:MM message (scheduled; process must stay online)
/hidden /scramble /anagram /wordle /hangman /wordchain /riddle /emojiquiz /mathquiz /guessnumber /fasttype /truefalse /trivia /puzzlehelp
/couple /setcoupleimage

SCORING
Correct answer on an active game: +3000 coins and +50 Aura.
Wrong answer to active game: -60 Aura (Aura floor is zero).
/protect 1d costs 500 coins; /protect 2d costs 1000 coins.
/top ranks coins; /auratop ranks Aura.

IMPORTANT LIMITS
- Telegram bots cannot discover every username or old username. Username commands only work if bot has seen and stored that user; ID/reply is more reliable.
- /approve and /decline work only for a real pending join request in that same group. Owner DM approval buttons remain supported.
- Database file nexusbot.sqlite3 stores scores, filters and profiles; back it up.
- This app also serves the dashboard on PORT (default 8080).

ADDITIONAL NOTES
- Google Search / /ask has been removed.
- Name history records changes only after the bot first starts tracking a user; /history shows full name, username, ID and timestamps. Telegram cannot reveal earlier historical names.
- Adult sticker removal checks only obvious adult-labelled sticker set names. It cannot reliably recognize explicit content inside arbitrary sticker images.
- Broadcast DM recipients must have pressed /start; groups must have been seen by the bot and it must still be a member.
- Scheduled broadcast time uses the host machine timezone and only runs while the process remains online. Join-request alerts include full name, username, user ID and local timestamp.
- Automatic translation uses external Google Translate via deep-translator; /translate hi or /translate en enables it per group.

ANTI-SPAM NOTES
- /antispam on enables flood and repeated-message checks (default ON). /antispam off disables it for that group; /antispam status shows current state.
- Seven messages within 8 seconds can trigger a 60-second mute; repeated identical text (4 times in 30 seconds) is deleted with a warning.
- Bot needs Delete Messages and Restrict Members permissions for full enforcement. Admins/owner are exempt. Tune thresholds in bot.py if desired.
- Join requests can be approved at no cost with the owner DM Approve button or /approve USER_ID in the relevant group. Approval only works for a real pending join request; it does not itself allow spam.
- Timestamps use the hosting machine local timezone. Set the host timezone correctly if you need a specific clock/time zone.


FREE / ANTI-SPAM EXEMPTION
- Reply to a member's message with /free to exempt them from anti-spam in this group.
- Or use /free USER_ID or /free @username (username must already be known to the bot).
- Use /unfree the same way to remove the exemption.
- This is a group anti-spam exemption, not Telegram's pending join-request approval.

TEXT & MEDIA FILTERS (owner only)
- /filter hello Hi there! — when a message contains "hello", bot replies with the saved response.
- Reply to a text message with /filter response text — saves a filter based on that message.
- Reply to a sticker/photo/video/audio/document/voice message with /filter response text — saves an exact-media filter.
- /filter sticker Please don't spam stickers — responds to any sticker.
- Supported media-type filters: sticker, photo, video, animation, document, audio, voice, video_note.
- /filters lists the saved filters.
