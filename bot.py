import os
import asyncio
import random
import time
import re
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from waitress import serve
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatJoinRequestHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from db import (
    init_db, upsert_user, get_user_by_username, get_user_by_id, add_log,
    is_owner, get_owner_id, get_filters, add_filter, remove_filter,
    add_media_filter, get_media_filters, get_media_filter, remove_media_filter,
    list_users, list_logs, get_settings, set_setting, get_stats, upsert_group_user, list_group_users,
    mark_dm_started, has_dm_started, adjust_score, get_score, leaderboard, buy_aura_protection,
    get_name_history, remember_group, get_known_groups, get_broadcast_users,
    set_free_member, is_free_member
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
WEB_SECRET = os.getenv("WEB_SECRET", "").strip()
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
PORT = int(os.getenv("PORT", "8080"))
COUPLE_COOLDOWN_SECONDS = 6 * 60 * 60
ACTIVE_PUZZLES = {}
POSITIVE_WORDS = set("love lovely loved loving kind kindness nice good great awesome amazing excellent beautiful happy happiness smile smiling joy joyful positive helpful help thanks thank you welcome please respect respectful honest honesty brave courage confident calm peaceful peace friendly friend friendship support supportive care caring sweet wonderful fantastic perfect brilliant smart clever creative success successful win winner proud proudness hope hopeful trust trusted trustful safe secure fair fairness gentle generous generousity polite politey patient patience grateful gratitude appreciate appreciated admire admirable strong strength healthy healing comfort comforted relax relaxed relaxes laugh laughter funny hilarious cool cute adorable gorgeous pretty handsome delightful inspiring inspire inspired motivated motivate motivate dream dreamer dreamful bless blessed blessing lucky fortunate celebrate celebration congratulations congrats welcome yay yes agree correct true accurate reliable loyal loyalist dependable awesome superb splendid marvelous outstanding remarkable radiant sunshine cheerful cheerful bright warm warmth tender tenderly compassionate compassion empathy empathetic understanding thoughtful thoughtfulness considerate consideration generous-hearted uplifting encourage encouraged encouragement achieve achieved achievement improve improved progress progressful thrive thriving flourish flourishing freedom harmony harmony loveable lovable trustful truthful truth sincere sincerity integrity dignified dignity forgive forgiveness forgiven sorry apology apologize reconcile reconciliation calmness serenity tranquil tranquilize relief relieved relief soothing soothe comfort comforting safe safety secure security balance balanced mindful mindfulness wisdom wise intelligent insight insightful learn learning teach teacher educate education curious curiosity wonder wonderful valuable worthy worthiness capable capability talent talented skillful skill achievement patience resilient resilience persistent persistence determined determination focus focused clarity clear claritywise optimistic optimism faith faithfulness reliable dependable dependable cheer cheer up bravo kudos respectfulness unity together togetherness community teamwork team helpfulness".split())
NEGATIVE_WORDS = set("hate hateful hated hatred bad awful terrible horrible worst ugly stupid idiot dumb fool foolish useless worthless trash garbage disgusting annoying annoyingness angry anger mad furious rage rude impolite disrespect disrespectful cruel cruelty mean toxic toxicness evil wicked nasty dirty disgusting liar lying lie false fake fraud scam cheat cheating cheated betray betrayal traitor selfish selfishness greedy greed jealous jealousy envy envious sad sadness unhappy miserable depressed lonely loneliness hopeless despair despairing fear afraid scared panic anxious anxiety worry worried stress stressed tired exhausted weak weakness failure fail failed lose loser loss wrong incorrect mistake error broken damage harm harmful hurt hurting pain painful suffer suffering sick illness danger dangerous unsafe insecure unfair injustice unfairness guilty shame ashamed regret regretful blame blameworthy fault careless reckless lazy laziness boring bored dull boringness annoying irritating irritatingly irritating rude harsh harshly violent violence aggressive aggression threat threaten threatful curse cursed damn hell damnation pathetic coward cowardly cowardice stupidly clueless ignorant ignorance arrogant arrogance prideful conceited vain vanity boast boastful brag bragging complain complaint whining whiny pessimistic pessimism hopelessness uselessness failureful miserable misery grief grieving sorrow sorrowful weep crying cry tears tearful depressed depress depressing gloomy doom doomed failure shameful disgrace disgraceful insult insulting offensive offense abusive abuse bully bullying bullied harassment harass humiliation humiliate humiliating failure fail badly weakling incompetent incompetence unreliable untrustworthy dishonest dishonesty unkind cold-hearted heartless insensitive inconsiderate selfish rude hateful spite spiteful malicious malice resentment resentful bitter bitterness hostile hostility conflict fight fighting argument argue attack attacked dangerous risk risky panic stress tension tense frustrated frustration irritated irritation annoyed annoyance regret guilt guilty shame embarrassment embarrassing awkward awkwardness".split())


if not WEB_SECRET:
    raise RuntimeError("Set a long random WEB_SECRET in .env")
if not DASHBOARD_PASSWORD:
    raise RuntimeError("Set DASHBOARD_PASSWORD in .env")
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN in .env")
if OWNER_ID <= 0:
    raise RuntimeError("Set numeric OWNER_ID in .env")

init_db(OWNER_ID)
app = Flask(__name__)
app.secret_key = WEB_SECRET

DASH = r"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexus Bot Control</title><style>
:root{--bg:#0b0b0e;--panel:#15151b;--line:#2a2930;--gold:#d9b45b;--muted:#aaa8b3}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#f5f2eb;font:15px/1.5 Inter,system-ui,Arial}
header{padding:24px max(20px,calc((100% - 1120px)/2));border-bottom:1px solid var(--line);background:#101014;display:flex;justify-content:space-between;align-items:center}
.brand{font-size:22px;font-weight:800;letter-spacing:.3px}.brand span{color:var(--gold)}main{max-width:1120px;margin:26px auto;padding:0 18px}
h2{font-size:19px;margin:0 0 14px}.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:16px}
.stat{font-size:30px;font-weight:800;color:var(--gold)}input,select,button{font:inherit;border-radius:9px;border:1px solid #3b3943;padding:10px 12px;background:#101015;color:#fff;max-width:100%}
button,.btn{background:var(--gold);color:#17130a;border:0;font-weight:750;cursor:pointer;text-decoration:none;display:inline-block}
form{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--gold)}
.notice{padding:10px 12px;border-radius:10px;background:#242016;color:#f1dca5;margin:12px 0}.danger{color:#ff9999}
@media(max-width:650px){header{padding:18px;align-items:flex-start;gap:12px}table{font-size:12px}td,th{padding:7px}}
</style></head><body>
<header><div class="brand">🌹 Nexus Bot <span>Control</span><div class="muted" style="font-size:12px;font-weight:400">Group Management Console</div></div>
{% if logged %}<a class="btn" href="/logout">Logout</a>{% endif %}</header><main>
{% with messages=get_flashed_messages() %}{% if messages %}{% for m in messages %}<div class="notice">{{m}}</div>{% endfor %}{% endif %}{% endwith %}
{% if not logged %}
<div class="card" style="max-width:440px;margin:60px auto"><h2>Admin sign in</h2><p class="muted">Only the configured dashboard account can access this console.</p>
<form method="post" action="/login" style="display:block"><p><input name="username" placeholder="Username" required style="width:100%"></p><p><input name="password" type="password" placeholder="Password" required style="width:100%"></p><button>Sign in</button></form></div>
{% else %}
<div class="grid">
<div class="card"><div class="muted">Tracked users</div><div class="stat">{{stats.users}}</div></div>
<div class="card"><div class="muted">Media filters</div><div class="stat">{{stats.media_filters}}</div></div>
<div class="card"><div class="muted">Saved filters</div><div class="stat">{{stats.filters}}</div></div>
<div class="card"><div class="muted">Moderation logs</div><div class="stat">{{stats.logs}}</div></div>
</div>
<div class="card"><h2>Keyword filters</h2><p class="muted">These filters apply in groups where this bot is an admin and can delete messages.</p>
<form method="post" action="/filter"><input name="keyword" placeholder="Keyword to match" required><input name="response" placeholder="Optional reply (can be blank)"><button>Add filter</button></form>
{% if filters %}<table><tr><th>Keyword</th><th>Response</th><th>Action</th></tr>{% for f in filters %}<tr><td>{{f.keyword}}</td><td>{{f.response or 'Delete only'}}</td><td><form method="post" action="/filter/delete"><input type="hidden" name="keyword" value="{{f.keyword}}"><button>Delete</button></form></td></tr>{% endfor %}</table>{% else %}<p class="muted">No text filters yet.</p>{% endif %}</div>
<div class="card"><h2>Sticker & media auto-replies</h2><p class="muted">Reply to any sticker/media in Telegram with <code>/filter your reply text</code> to save it.</p>
{% if media_filters %}<table><tr><th>Media type</th><th>Response</th><th>Action</th></tr>{% for f in media_filters %}<tr><td>{{f.media_type}}</td><td>{{f.response or 'No reply'}}</td><td><form method="post" action="/media-filter/delete"><input type="hidden" name="media_key" value="{{f.media_key}}"><button>Delete</button></form></td></tr>{% endfor %}</table>{% else %}<p class="muted">No media filters yet.</p>{% endif %}</div>
<div class="card"><h2>Recent users</h2><table><tr><th>User ID</th><th>Username</th></tr>
{% for u in users %}<tr><td>{{u.user_id}}</td><td>{{'@'+u.username if u.username else '—'}}</td></tr>{% endfor %}</table></div>
<div class="card"><h2>Recent audit log</h2><table><tr><th>Time (UTC)</th><th>Actor</th><th>Action</th><th>Target</th><th>Details</th></tr>
{% for l in logs %}<tr><td>{{l.created_at}}</td><td>{{l.actor_id}}</td><td>{{l.action}}</td><td>{{l.target_id or '—'}}</td><td>{{l.details}}</td></tr>{% endfor %}</table></div>
{% endif %}</main></body></html>
"""

def dashboard_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper

@app.get("/")
def home():
    logged = bool(session.get("logged_in"))
    return render_template_string(
        DASH, logged=logged,
        stats=get_stats() if logged else {},
        users=list_users(50) if logged else [],
        filters=get_filters() if logged else [],
        media_filters=get_media_filters() if logged else [],
        logs=list_logs(30) if logged else []
    )

@app.post("/login")
def login():
    if request.form.get("username") == DASHBOARD_USER and request.form.get("password") == DASHBOARD_PASSWORD:
        session.clear()
        session["logged_in"] = True
        return redirect(url_for("home"))
    flash("Invalid login.")
    return redirect(url_for("home"))

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

def resolve_dashboard_target(value):
    value = (value or "").strip()
    if value.startswith("@"):
        user = get_user_by_username(value[1:])
        return user["user_id"] if user else None
    if value.isdigit():
        return int(value)
    return None

@app.post("/filter")
@dashboard_login_required
def filter_add():
    keyword = (request.form.get("keyword") or "").strip().lower()
    response = (request.form.get("response") or "").strip()
    if not keyword or len(keyword) > 100:
        flash("Keyword must be 1–100 characters.")
    else:
        add_filter(keyword, response)
        add_log(OWNER_ID, "filter_add", None, f"keyword={keyword}")
        flash("Filter saved.")
    return redirect(url_for("home"))

@app.post("/filter/delete")
@dashboard_login_required
def filter_delete():
    keyword = (request.form.get("keyword") or "").strip().lower()
    remove_filter(keyword)
    add_log(OWNER_ID, "filter_delete", None, f"keyword={keyword}")
    flash("Filter deleted.")
    return redirect(url_for("home"))

@app.post("/media-filter/delete")
@dashboard_login_required
def media_filter_delete():
    key = (request.form.get("media_key") or "").strip()
    remove_media_filter(key)
    add_log(OWNER_ID, "media_filter_delete", None, f"key={key[:100]}")
    flash("Media filter deleted.")
    return redirect(url_for("home"))

async def safe_reply(update, text):
    if update.effective_message:
        await update.effective_message.reply_text(text)

def actor_is_owner(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == OWNER_ID)

async def tracked(update: Update):
    user = update.effective_user
    chat = update.effective_chat
    if user:
        upsert_user(user.id, user.username, user.first_name)
        if chat and chat.type in ("group", "supergroup"):
            upsert_group_user(chat.id, user.id, user.username, user.first_name)

async def command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    user = update.effective_user
    chat = update.effective_chat
    if user and chat and chat.type == "private":
        mark_dm_started(user.id)
    username = getattr(context.bot, "username", None)
    add_group_url = f"https://t.me/{username}?startgroup=true" if username else "https://t.me/"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Nexus Bot to Group", url=add_group_url)],
        [InlineKeyboardButton("📚 Help & All Commands", callback_data="start:help")],
        [InlineKeyboardButton("🏓 Ping", callback_data="start:ping")],
    ])
    msg = update.effective_message
    if msg:
        private_note = "\n\n✅ DM activated — you can now use group games after joining a group." if chat and chat.type == "private" else "\n\n📩 Open my DM and press Start before playing games in your group."
        await msg.reply_text(
            "🌹 𝗥𝗢𝗦𝗘𝗕𝗢𝗧 𝗨𝗟𝗧𝗜𝗠𝗔𝗧𝗘\n\n"
            "✨ Couple of the day • Word games • Puzzles\n"
            "🛡️ Ban/mute • Text & media filters • User info\n"
            "✨ Group points • Aura score • Leaderboards • Aura protection\n"
            "⚙️ Group tools • Join-request approvals • Free anti-spam exemptions • User history • Translation • Broadcast\n\n"
            "Use /help to see every command, /ping to test response, or Add to Group to install me."
            + private_note,
            reply_markup=keyboard,
        )

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.perf_counter()
    msg = update.effective_message
    if msg:
        sent = await msg.reply_text("🏓 Pinging Nexus Bot…")
        elapsed = round((time.perf_counter() - start) * 1000)
        await sent.edit_text(f"🏓 **Pong!**\n⚡ Response: `{elapsed} ms`\n🌹 Nexus Bot is online.", parse_mode="Markdown")

def full_help_text():
    return (
        "🌹 NEXUS BOT ULTIMATE — ALL COMMANDS\n\n"
        "🚀 START & STATUS\n/start — welcome menu, Add to Group, Help\n/help — all commands\n/ping — response time\n/id — your ID and chat ID\n/info [@username|ID] or reply — user info\n\n"
        "🛡️ MODERATION (group admins/owner)\n/ban [@username|ID] or reply\n/unban [@username|ID] or reply\n/mute [target] [minutes] or reply\n/unmute [target] or reply\n/approve USER_ID or /decline USER_ID — pending join request only\n/antispam on|off, /free, /unfree|status — flood and repeated-message protection (default ON)\n\n"
        "🧹 FILTERS\n/filter keyword response — text keyword auto-response\nReply to sticker/photo/video/GIF/document/audio/voice with /filter response text — media auto-reply\n/filters — list saved filters\n\n"
        "🧾 USER HISTORY\n/history [@username|ID] or reply — current full name, username, user ID, profile time and saved old names with timestamps (only from when tracking began)\n\n"
        "🌐 LANGUAGE\n/translate hi|en — toggle automatic translation to Hindi or English in groups; /translate off disables it\n\n"
        "📣 OWNER BROADCAST\n/broadcast message — send to known groups and users who started DM\n/broadcast_at YYYY-MM-DD HH:MM message — schedule (server local time)\n\n"
        "🔞 ADULT STICKER FILTER\nAutomatically removes stickers when their sticker-set name clearly matches configured adult keywords. This cannot reliably identify explicit images from pixels alone.\n\n"
        "💞 COUPLES\n/couple — random group couple every 6 hours; reply to a member with /couple for a fresh pair\n/setcoupleimage — owner: reply to a photo to set couple image\n\n"
        "✨ AURA & LEADERBOARDS\n/top — group total-points leaderboard\n/auratop — group Aura leaderboard\n/points — show your points and Aura\n/protect 1d — protect Aura from losses for 1 day (500 coins)\n/protect 2d — protect Aura from losses for 2 days (1000 coins)\nPositive words add Aura; negative words can reduce Aura. Scores are separate per group.\n\n🧩 WORD GAMES & PUZZLES\n/hidden — missing-letter word\n/scramble — unscramble letters\n/anagram — rearrange letters\n/wordle — guess hidden word\n/hangman — guess the word\n/wordchain — word-chain prompt\n/fasttype — typing challenge\n/guessnumber — number guessing\n/riddle — solve a riddle\n/emojiquiz — emoji puzzle\n/mathquiz — maths challenge\n/truefalse — true/false quiz\n/trivia — general knowledge\n/puzzlehelp — game list\n\n"
        "📩 IMPORTANT: Open the bot in private chat and press Start before playing group games or using /couple. Each player must start the bot in DM to submit game answers. Moderation and filters continue to protect the group.\n"
        "Username lookup only works for users the bot has previously seen; numeric IDs and reply targets are more reliable."
    )

async def start_buttons_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if query.data == "start:help":
        await query.answer()
        await query.message.reply_text(full_help_text())
    elif query.data == "start:ping":
        await query.answer()
        await query.message.reply_text("🏓 Pong! Nexus Bot is online. Use /ping for response timing.")
    else:
        await query.answer()

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    await safe_reply(update, full_help_text())

async def dm_game_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Games require each player to have pressed /start in the bot's private chat."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or chat.type not in ("group", "supergroup"):
        return True
    if has_dm_started(user.id):
        return True
    bot_username = getattr(context.bot, "username", None)
    dm_url = f"https://t.me/{bot_username}?start=play" if bot_username else "https://t.me/"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Start Nexus Bot in DM", url=dm_url)]])
    msg = update.effective_message
    if msg:
        await msg.reply_text(
            "🔒 To play games or use /couple, first open Nexus Bot in private chat and press Start. "
            "Then return here. Each player must do this once.", reply_markup=keyboard
        )
    return False

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    user = update.effective_user
    chat = update.effective_chat
    await safe_reply(update, f"Your ID: {user.id if user else 'unknown'}\nChat ID: {chat.id if chat else 'unknown'}")

async def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reply target wins; otherwise accept numeric ID or previously seen @username.
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user
        upsert_user(target.id, target.username, target.first_name)
        return target.id
    if not context.args:
        return None
    token = context.args[0].strip()
    if token.isdigit():
        return int(token)
    if token.startswith("@"):
        found = get_user_by_username(token[1:])
        return found["user_id"] if found else None
    return None

async def caller_is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if actor_is_owner(update):
        return True
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or chat.type not in ("group", "supergroup"):
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False

async def moderation_target(update, context):
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can use this command.")
        return None
    if not update.effective_chat or update.effective_chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use this moderation command inside a group.")
        return None
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Target not found. Reply to a user's message, use numeric ID, or use a username already seen by the bot.")
        return None
    return target

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await moderation_target(update, context)
    if not target: return
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id, target)
        add_log(update.effective_user.id, "ban", target, f"chat={chat_id}")
        await safe_reply(update, f"✅ Banned user ID {target}.")
    except Exception as e:
        await safe_reply(update, f"Could not ban user {target}. Check bot admin permissions and target ID. ({type(e).__name__})")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await moderation_target(update, context)
    if not target: return
    chat_id = update.effective_chat.id
    try:
        await context.bot.unban_chat_member(chat_id, target, only_if_banned=True)
        add_log(update.effective_user.id, "unban", target, f"chat={chat_id}")
        await safe_reply(update, f"✅ Unbanned user ID {target}.")
    except Exception as e:
        await safe_reply(update, f"Could not unban user {target}. ({type(e).__name__})")

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await moderation_target(update, context)
    if not target: return
    try:
        minutes = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 60
        minutes = max(1, min(minutes, 10080))
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        perms = ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False,
            can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
            can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
            can_add_web_page_previews=False)
        await context.bot.restrict_chat_member(update.effective_chat.id, target, permissions=perms, until_date=until)
        add_log(update.effective_user.id, "mute", target, f"minutes={minutes}; chat={update.effective_chat.id}")
        await safe_reply(update, f"🔇 Muted user ID {target} for {minutes} minutes.")
    except Exception as e:
        await safe_reply(update, f"Could not mute user {target}. Check bot permissions. ({type(e).__name__})")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await moderation_target(update, context)
    if not target: return
    try:
        perms = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
            can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True)
        await context.bot.restrict_chat_member(update.effective_chat.id, target, permissions=perms)
        add_log(update.effective_user.id, "unmute", target, f"chat={update.effective_chat.id}")
        await safe_reply(update, f"🔊 Unmuted user ID {target}.")
    except Exception as e:
        await safe_reply(update, f"Could not unmute user {target}. ({type(e).__name__})")

async def free_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exempt a group member from anti-spam by reply, numeric ID, or known @username."""
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can use /free.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /free in a group. Reply to a member, or use /free USER_ID /free @username.")
        return
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Usage: reply to a member with /free, or use /free USER_ID /free @username (username must be known to the bot).")
        return
    set_free_member(chat.id, target, True)
    add_log(update.effective_user.id, "free_member", target, f"chat={chat.id}")
    await safe_reply(update, f"✅ User ID {target} is now free from anti-spam in this group. Use /unfree to remove the exemption.")

async def unfree_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can use /unfree.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /unfree in a group.")
        return
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Usage: reply to a member with /unfree, or /unfree USER_ID /unfree @username.")
        return
    set_free_member(chat.id, target, False)
    add_log(update.effective_user.id, "unfree_member", target, f"chat={chat.id}")
    await safe_reply(update, f"✅ Anti-spam exemption removed for user ID {target} in this group.")

async def antispam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle basic anti-flood and repeated-message protection for this group."""
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can control anti-spam.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /antispam on or /antispam off in a group.")
        return
    arg = context.args[0].lower() if context.args else "status"
    key = f"antispam:{chat.id}"
    if arg in ("on", "enable", "enabled"):
        set_setting(key, "1")
        await safe_reply(update, "🛡️ Anti-spam ON. Flood and repeated messages will be removed; repeated offenders may be muted briefly.")
    elif arg in ("off", "disable", "disabled"):
        set_setting(key, "0")
        await safe_reply(update, "⚠️ Anti-spam OFF for this group.")
    elif arg == "status":
        enabled = get_settings().get(key, "1") != "0"
        await safe_reply(update, f"🛡️ Anti-spam is {'ON' if enabled else 'OFF'}. Use /antispam on or /antispam off.")
    else:
        await safe_reply(update, "Usage: /antispam on | /antispam off | /antispam status")

async def check_antispam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not chat or not user or user.is_bot or chat.type not in ("group", "supergroup"):
        return False
    if get_settings().get(f"antispam:{chat.id}", "1") == "0":
        return False
    # /free exemptions are scoped to this group and survive bot restarts.
    if is_free_member(chat.id, user.id):
        return False
    # Never apply the anti-spam filter to admins/owner.
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if user.id == OWNER_ID or member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return False
    except Exception:
        pass
    now = time.time()
    bucket = context.application.bot_data.setdefault("spam_activity", {})
    key = (chat.id, user.id)
    state = bucket.setdefault(key, {"times": [], "texts": []})
    state["times"] = [t for t in state["times"] if now - t < 8]
    state["times"].append(now)
    body = (msg.text or msg.caption or "[media]").strip().casefold()
    if body:
        state["texts"] = [(t, text) for t, text in state["texts"] if now - t < 30]
        state["texts"].append((now, body[:300]))
    flood = len(state["times"]) >= 7
    repeats = sum(1 for _, text in state["texts"] if text == body) >= 4 and body != "[media]"
    if not (flood or repeats):
        return False
    try:
        await msg.delete()
    except Exception:
        # Bot needs Delete Messages permission to remove spam.
        pass
    add_log(0, "anti_spam_trigger", user.id, f"chat={chat.id}; flood={flood}; repeats={repeats}")
    if flood:
        try:
            until = datetime.now(timezone.utc) + timedelta(seconds=60)
            perms = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(chat.id, user.id, permissions=perms, until_date=until)
            await context.bot.send_message(chat.id, f"🛡️ Anti-spam: {user.full_name} muted for 60 seconds due to flooding.")
        except Exception:
            await context.bot.send_message(chat.id, f"🛡️ Anti-spam detected flooding from {user.full_name}. Bot needs Restrict Members permission to mute.")
    else:
        await context.bot.send_message(chat.id, f"⚠️ {user.full_name}, repeated messages are not allowed.")
    state["times"] = []
    state["texts"] = []
    return True

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Use /history USER_ID, /history @username, or reply to the user's message with /history.")
        return
    rows = get_name_history(target, 50)
    current = get_user_by_id(target)
    if not current:
        await safe_reply(update, f"No saved profile for user ID {target}. The bot can only show details it has observed.")
        return
    now_local = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z (local time)")
    current_name = current.get("first_name") or "(no name saved)"
    current_username = "@" + current["username"] if current.get("username") else "(no username)"
    lines = [f"🧾 USER HISTORY", f"Full name: {current_name}", f"Username: {current_username}", f"User ID: {target}", f"Profile last seen: {current.get('updated_at') or 'unknown'}", f"Checked at: {now_local}", "", "Previous saved names/usernames:"]
    if rows:
        lines.extend(f"• {r['changed_at']} — Name: {r['first_name'] or '(no name)'} | Username: {'@'+r['username'] if r['username'] else '(no username)'}" for r in rows)
    else:
        lines.append("• No changes recorded yet. History begins only after the bot starts tracking this user.")
    await safe_reply(update, "\n".join(lines))

async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update) and not await caller_is_admin(update, context):
        await safe_reply(update, "Only the owner or a group admin can change translation settings.")
        return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /translate hi, /translate en, or /translate off in a group.")
        return
    value = context.args[0].lower() if context.args else ""
    if value not in ("hi", "en", "off"):
        await safe_reply(update, "Usage: /translate hi | /translate en | /translate off")
        return
    set_setting(f"translate:{chat.id}", value)
    await safe_reply(update, f"🌐 Automatic translation: {'Hindi' if value == 'hi' else 'English' if value == 'en' else 'OFF'}")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Owner only.")
        return
    text_body = " ".join(context.args).strip()
    if not text_body:
        await safe_reply(update, "Usage: /broadcast your message\nScheduled: /broadcast_at YYYY-MM-DD HH:MM your message")
        return
    dm_ids = get_broadcast_users()
    group_ids = get_known_groups()
    targets = [("dm", int(x)) for x in dm_ids] + [("group", int(x)) for x in group_ids]
    sent = failed = 0
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    for kind, target_id in targets:
        try:
            await context.bot.send_message(chat_id=target_id, text=f"📣 Nexus Bot Broadcast\n🕒 {stamp}\n\n{text_body}")
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1
    await safe_reply(update, f"📣 Broadcast finished.\nSent: {sent}\nFailed/unavailable: {failed}\nTargets: {len(targets)}")

async def broadcast_at_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Owner only.")
        return
    raw = update.effective_message.text.partition(" ")[2].strip()
    parts = raw.split(maxsplit=2)
    if len(parts) < 3:
        await safe_reply(update, "Usage: /broadcast_at YYYY-MM-DD HH:MM your message\nExample: /broadcast_at 2026-10-22 20:30 Hello group!")
        return
    try:
        when = datetime.strptime(parts[0] + " " + parts[1], "%Y-%m-%d %H:%M").astimezone()
    except ValueError:
        await safe_reply(update, "Date/time format galat hai. Use YYYY-MM-DD HH:MM (server local time).")
        return
    message_text = parts[2]
    seconds = (when - datetime.now().astimezone()).total_seconds()
    if seconds <= 0:
        await safe_reply(update, "Scheduled time future mein hona chahiye.")
        return
    async def deliver():
        await asyncio.sleep(seconds)
        dm_ids = get_broadcast_users()
        group_ids = get_known_groups()
        targets = [("dm", int(x)) for x in dm_ids] + [("group", int(x)) for x in group_ids]
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        sent = failed = 0
        for _, target_id in targets:
            try:
                await context.bot.send_message(chat_id=target_id, text=f"📣 Scheduled Nexus Bot Broadcast\n🕒 {stamp}\n\n{message_text}")
                sent += 1
                await asyncio.sleep(0.04)
            except Exception:
                failed += 1
        try:
            await context.bot.send_message(OWNER_ID, f"Scheduled broadcast completed. Sent: {sent}; failed: {failed}.")
        except Exception:
            pass
    context.application.create_task(deliver())
    await safe_reply(update, f"⏰ Broadcast scheduled for {when.strftime('%Y-%m-%d %H:%M %Z')}\nNote: scheduled task runs only while this bot process stays online.")

async def maybe_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not msg.text or not chat or chat.type not in ("group", "supergroup") or not user or user.is_bot or msg.text.startswith("/"):
        return
    target = get_settings().get(f"translate:{chat.id}", "off")
    if target not in ("hi", "en"):
        return
    try:
        from deep_translator import GoogleTranslator
        from langdetect import detect
        source = detect(msg.text)
        if source == target or len(msg.text.strip()) < 3:
            return
        translated = await asyncio.to_thread(GoogleTranslator(source="auto", target=target).translate, msg.text[:4000])
        if translated and translated.strip().casefold() != msg.text.strip().casefold():
            label = "Hindi" if target == "hi" else "English"
            await msg.reply_text(f"🌐 {label} translation:\n{translated}")
    except Exception:
        # Keep ordinary group chat working if translation service is unavailable.
        return

ADULT_STICKER_TERMS = ("adult", "18plus", "18_plus", "nsfw", "xxx", "sex", "nude", "nudes", "porn", "hentai")
async def remove_adult_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not msg.sticker or not chat or chat.type not in ("group", "supergroup") or (user and user.is_bot):
        return False
    sticker = msg.sticker
    set_name = (sticker.set_name or "").casefold()
    flagged = any(term in set_name for term in ADULT_STICKER_TERMS)
    # This is metadata-based detection only; Telegram does not provide an adult-content flag.
    if flagged:
        try:
            member = await context.bot.get_chat_member(chat.id, context.bot.id)
            if member.status == ChatMemberStatus.ADMINISTRATOR:
                await msg.delete()
                await context.bot.send_message(chat.id, "🔞 Adult-labelled sticker set detected; sticker removed.")
                add_log(0, "adult_sticker_removed", user.id if user else None, f"chat={chat.id}; set={set_name[:100]}")
                return True
        except Exception:
            pass
    return False

def media_signature(message):
    if not message:
        return None
    if message.sticker:
        return ("sticker", message.sticker.file_unique_id)
    if message.photo:
        return ("photo", message.photo[-1].file_unique_id)
    for attr, kind in (("video", "video"), ("animation", "animation"), ("document", "document"),
                       ("audio", "audio"), ("voice", "voice"), ("video_note", "video_note")):
        item = getattr(message, attr, None)
        if item:
            return (kind, item.file_unique_id)
    return None

async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Only the bot owner can add or change filters.")
        return
    msg = update.effective_message
    response = " ".join(context.args).strip()[:500]
    replied = msg.reply_to_message if msg else None

    # Type-wide media filters: /filter sticker response text
    media_types = {"sticker", "photo", "video", "animation", "document", "audio", "voice", "video_note"}
    if context.args and context.args[0].lower() in media_types and len(context.args) >= 2 and not (replied and (replied.text or replied.caption)):
        media_type = context.args[0].lower()
        response = " ".join(context.args[1:]).strip()[:500]
        key = add_media_filter(media_type, "*", response)
        add_log(update.effective_user.id, "media_type_filter_add", None, f"type={media_type}; key={key}")
        await safe_reply(update, f"✅ All {media_type} messages will trigger this reply: {response}")
        return

    signature = media_signature(replied)
    if signature:
        if not response:
            await safe_reply(update, "Usage: reply to a sticker/media message with /filter your response text")
            return
        media_type, unique_id = signature
        key = add_media_filter(media_type, unique_id, response)
        add_log(update.effective_user.id, "media_filter_add", None, f"type={media_type}; key={key}")
        await safe_reply(update, f"✅ Exact {media_type} filter saved. When the same media is sent in a group, I will reply: {response}")
        return

    if replied and (replied.text or replied.caption):
        trigger = (replied.text or replied.caption or "").strip()[:100].lower()
        if not response:
            await safe_reply(update, "Reply to a text message with /filter your response text")
            return
        add_filter(trigger, response)
        add_log(update.effective_user.id, "filter_add_from_reply", None, f"keyword={trigger[:80]}")
        await safe_reply(update, f"✅ Reply-based text filter saved for: {trigger}")
        return

    if len(context.args) < 2:
        await safe_reply(update, "Usage: /filter keyword response text; reply to text/media with /filter response; or /filter sticker|photo|video|audio|document|voice|animation|video_note response.")
        return
    keyword = context.args[0].lower()[:100]
    response = " ".join(context.args[1:])[:500]
    add_filter(keyword, response)
    add_log(update.effective_user.id, "filter_add", None, f"keyword={keyword}")
    await safe_reply(update, f"✅ Text filter added for: {keyword}")

async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    rows = get_filters()
    media_rows = get_media_filters()
    lines = [f"• Text: {r['keyword']} → {r['response'] or '[delete only]'}" for r in rows[:30]]
    lines += [f"• Media: {r['media_type']} → {r['response'] or '[no reply]'} (key {r['media_key'][:24]}…)" for r in media_rows[:30]]
    if not lines:
        await safe_reply(update, "No filters configured.")
    else:
        await safe_reply(update, "Saved filters:\n" + "\n".join(lines))

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Usage: /info @username or reply to a message. Username must be known to the bot.")
        return
    row = get_user_by_id(target)
    if row:
        await safe_reply(update, f"User ID: {row['user_id']}\nUsername: @{row['username']}" if row["username"] else f"User ID: {row['user_id']}\nUsername: not set")
    else:
        await safe_reply(update, f"User ID: {target}\nNo saved profile yet.")

async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    if not req:
        return
    upsert_user(req.from_user.id, req.from_user.username, req.from_user.first_name)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"jr:approve:{req.chat.id}:{req.from_user.id}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"jr:decline:{req.chat.id}:{req.from_user.id}")
    ]])
    try:
        request_time = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z (local time)")
        username_text = "@" + req.from_user.username if req.from_user.username else "(no username)"
        await context.bot.send_message(
            OWNER_ID,
            f"🔔 JOIN REQUEST\nGroup: {req.chat.title or req.chat.id}\n"
            f"Full name: {req.from_user.full_name}\nUsername: {username_text}\n"
            f"User ID: {req.from_user.id}\nRequest received: {request_time}",
            reply_markup=keyboard
        )
    except Exception:
        pass

async def join_request_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if not query.from_user or query.from_user.id != OWNER_ID:
        await query.answer("Owner only.", show_alert=True)
        return
    try:
        _, action, chat_id, user_id = query.data.split(":")
        chat_id, user_id = int(chat_id), int(user_id)
        if action == "approve":
            await context.bot.approve_chat_join_request(chat_id, user_id)
            add_log(OWNER_ID, "join_approved", user_id, f"chat={chat_id}")
            await query.edit_message_text(f"✅ Approved join request for user {user_id} in chat {chat_id}.")
        elif action == "decline":
            await context.bot.decline_chat_join_request(chat_id, user_id)
            add_log(OWNER_ID, "join_declined", user_id, f"chat={chat_id}")
            await query.edit_message_text(f"❌ Declined join request for user {user_id} in chat {chat_id}.")
        else:
            await query.answer("Unknown action.", show_alert=True)
            return
        await query.answer("Done")
    except Exception as e:
        await query.answer("Action failed. Check bot permissions and whether request is still pending.", show_alert=True)
        print(f"Join request action error: {type(e).__name__}")

async def points_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        await safe_reply(update, "Use /points inside a group."); return
    row = get_score(chat.id, user.id) or {"total_points": 0, "aura_points": 0, "aura_protect_until": 0}
    import datetime as _dt
    protection = "Active until " + _dt.datetime.fromtimestamp(row["aura_protect_until"], _dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if row["aura_protect_until"] and row["aura_protect_until"] > time.time() else "Not active"
    await safe_reply(update, f"🌹 NEXUS BOT PROFILE\n\n🪙 Coins: {row['total_points']}\n✨ Aura: {row['aura_points']}\n🛡️ Aura protection: {protection}\n\nUse /top and /auratop to see this group's leaderboard.")

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, aura=False):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use this command inside a group."); return
    rows = leaderboard(chat.id, "aura_points" if aura else "total_points", 10)
    title = "✨ AURA TOPLIST" if aura else "🪙 GROUP COIN TOPLIST"
    if not rows:
        await safe_reply(update, title + "\n\nNo scores yet — play a game or chat to start earning points!"); return
    lines = []
    for i, r in enumerate(rows, 1):
        name = ("@" + r["username"]) if r.get("username") else (r.get("first_name") or str(r["user_id"]))
        value = r["aura_points"] if aura else r["total_points"]
        lines.append(f"{i}. {name} — {value} {'Aura' if aura else 'coins'}")
    await safe_reply(update, title + "\n\n" + "\n".join(lines))

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await leaderboard_cmd(update, context, False)

async def auratop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await leaderboard_cmd(update, context, True)

async def giveaura_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        await safe_reply(update, "Use /giveaura in a group."); return
    target = await resolve_target(update, context)
    if not target or not context.args:
        await safe_reply(update, "Reply to a member with /giveaura amount, or use /giveaura @username amount."); return
    amount_token = context.args[-1]
    if not amount_token.isdigit() or not 1 <= int(amount_token) <= 1000000:
        await safe_reply(update, "Usage: /giveaura @username amount (1–1000000)"); return
    amount = int(amount_token)
    if target == user.id:
        await safe_reply(update, "You cannot give Aura to yourself."); return
    sender = get_score(chat.id, user.id) or {"aura_points": 0}
    if int(sender["aura_points"]) < amount:
        await safe_reply(update, f"Not enough Aura. You have {sender['aura_points']}."); return
    profile = get_user_by_id(target) or {"username": None, "first_name": str(target)}
    adjust_score(chat.id, user.id, user.username, user.first_name, aura_delta=-amount)
    received = adjust_score(chat.id, target, profile.get("username"), profile.get("first_name"), aura_delta=amount)
    display = "@" + profile["username"] if profile.get("username") else (profile.get("first_name") or str(target))
    await safe_reply(update, f"✨ {amount} Aura sent to {display}. Their total Aura: {received['aura_points']}.")

async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        await safe_reply(update, "Use /rob in a group."); return
    target = await resolve_target(update, context)
    if not target or target == user.id:
        await safe_reply(update, "Reply to a member with /rob [amount], or use /rob @username [amount]."); return
    profile = get_user_by_id(target) or {"username": None, "first_name": str(target)}
    target_score = get_score(chat.id, target) or {"aura_points": 0}
    available = int(target_score["aura_points"])
    if available <= 0:
        await safe_reply(update, "That member has no Aura to rob."); return
    amount = int(context.args[-1]) if context.args and context.args[-1].isdigit() else random.randint(1, min(100, available))
    amount = max(1, min(amount, 1000, available))
    display = "@" + profile["username"] if profile.get("username") else (profile.get("first_name") or str(target))
    if random.random() > 0.55:
        await safe_reply(update, "🚨 Rob failed! No Aura transferred."); return
    adjust_score(chat.id, target, profile.get("username"), profile.get("first_name"), aura_delta=-amount)
    result = adjust_score(chat.id, user.id, user.username, user.first_name, aura_delta=amount)
    await safe_reply(update, f"💰 Rob successful! {amount} Aura stolen from {display}. Your total Aura: {result['aura_points']}.")

async def approval_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await caller_is_admin(update, context):
        await safe_reply(update, "⛔ Only the owner or a group admin can approve/decline join requests."); return
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use this command in the group where the join request is pending."); return
    target = await resolve_target(update, context)
    if not target:
        await safe_reply(update, "Usage: /approve USER_ID or /decline USER_ID. Reply/username works only if the bot knows that user."); return
    command = (update.effective_message.text or "").split()[0].split("@")[0].lower()
    try:
        if command == "/approve":
            await context.bot.approve_chat_join_request(chat.id, target)
            await safe_reply(update, f"✅ Join request approved for user ID {target}.")
        else:
            await context.bot.decline_chat_join_request(chat.id, target)
            await safe_reply(update, f"❌ Join request declined for user ID {target}.")
    except Exception as e:
        await safe_reply(update, f"Could not process request. The user must have a pending join request and bot needs Manage Chat permissions. ({type(e).__name__})")

async def protect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user
    if not chat or chat.type not in ("group", "supergroup") or not user:
        await safe_reply(update, "Use /protect in a group."); return
    arg = context.args[0].lower() if context.args else ""
    plans = {"1d": (1, 500), "2d": (2, 1000)}
    if arg not in plans:
        await safe_reply(update, "🛡️ Aura Protection\n/protect 1d — 500 coins\n/protect 2d — 1000 coins\nProtection prevents Aura losses for the selected duration."); return
    days, cost = plans[arg]
    ok, row = buy_aura_protection(chat.id, user.id, user.username, user.first_name, days, cost)
    if not ok:
        await safe_reply(update, f"Not enough total points. {arg} protection costs {cost}; you have {row['total_points']}."); return
    expiry = __import__("datetime").datetime.fromtimestamp(row["aura_protect_until"], __import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    await safe_reply(update, f"🛡️ Aura Shield activated for {days} day(s)!\n💸 Cost: {cost} total points\n🏆 Remaining total points: {row['total_points']}\n✨ Current Aura: {row['aura_points']}\n⏳ Expires: {expiry}")

async def aura_for_message(update: Update):
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if not msg or not msg.text or not chat or chat.type not in ("group", "supergroup") or not user or user.is_bot or msg.text.startswith("/"):
        return
    words = re.findall(r"[a-zA-Z]+", msg.text.casefold())
    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)
    if pos or neg:
        # Per word: +5 Aura for positive words, -5 Aura for negative words.
        delta = max(-50, min(50, (pos - neg) * 5))
        before = get_score(chat.id, user.id) or {"aura_points": 0}
        row = adjust_score(chat.id, user.id, user.username, user.first_name, aura_delta=delta)
        actual_delta = int(row["aura_points"]) - int(before["aura_points"])
        if actual_delta and abs(actual_delta) >= 10:
            context_text = f"✨ +{actual_delta} Aura" if actual_delta > 0 else f"🌑 {actual_delta} Aura"
            # Avoid clutter: only announce notable adjustments.
            await msg.reply_text(f"{context_text} • Total Aura: {row['aura_points']}")
    else:
        # Ensure user appears on this group's points tables.
        adjust_score(chat.id, user.id, user.username, user.first_name)

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tracked(update)
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat or chat.type not in ("group", "supergroup"):
        return
    remember_group(chat.id, chat.title or str(chat.id))
    if await check_antispam(update, context):
        return
    if await remove_adult_sticker(update, context):
        return
    await maybe_translate(update, context)
    await aura_for_message(update)

    # Only DM-started members may submit answers to an active group puzzle.
    if msg.text and chat.id in ACTIVE_PUZZLES and update.effective_user:
        if not has_dm_started(update.effective_user.id):
            prompted = context.bot_data.setdefault("dm_prompted", set())
            prompt_key = (chat.id, update.effective_user.id)
            if prompt_key not in prompted:
                prompted.add(prompt_key)
                bot_username = getattr(context.bot, "username", None)
                dm_url = f"https://t.me/{bot_username}?start=play" if bot_username else "https://t.me/"
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Start Nexus Bot in DM", url=dm_url)]])
                await msg.reply_text("To answer this game, first press Start in Nexus Bot's private chat.", reply_markup=keyboard)
            return
        puzzle = ACTIVE_PUZZLES[chat.id]
        if time.time() - puzzle.get("started", 0) > 600:
            ACTIVE_PUZZLES.pop(chat.id, None)
        elif puzzle.get("kind") == "guessnumber" and msg.text.strip().isdigit() and int(msg.text.strip()) != int(puzzle["answer"]):
            guess = int(msg.text.strip())
            await msg.reply_text("⬆️ Higher!" if guess < int(puzzle["answer"]) else "⬇️ Lower!")
            return
        elif msg.text.strip().casefold() == puzzle["answer"]:
            ACTIVE_PUZZLES.pop(chat.id, None)
            scorer = update.effective_user
            score_row = adjust_score(chat.id, scorer.id, scorer.username, scorer.first_name, total_delta=3000, aura_delta=50)
            await msg.reply_text(f"🎉 WINNER: {scorer.first_name or 'player'}!\n🪙 +3000 coins • ✨ +50 Aura\n🏆 Total coins: {score_row['total_points']} • ✨ Total Aura: {score_row['aura_points']}\nStart another with /puzzlehelp.")
            return

    if msg.text and chat.id in ACTIVE_PUZZLES and update.effective_user and not update.effective_user.is_bot:
        puzzle = ACTIVE_PUZZLES.get(chat.id)
        if puzzle and time.time() - puzzle.get("started", 0) <= 600 and msg.text.strip().casefold() != puzzle["answer"]:
            row = adjust_score(chat.id, update.effective_user.id, update.effective_user.username, update.effective_user.first_name, aura_delta=-60)
            await msg.reply_text(f"❌ Wrong answer, {update.effective_user.first_name or 'player'}! -60 Aura. Total Aura: {row['aura_points']}")
            return

    signature = media_signature(msg)
    if signature:
        row = get_media_filter(signature[0], signature[1])
        if row and row["response"]:
            try:
                await msg.reply_text(row["response"])
                add_log(0, "media_filter_match", update.effective_user.id if update.effective_user else None,
                        f"type={signature[0]}; chat={chat.id}")
            except Exception:
                pass
        return

    if not msg.text:
        return
    text = msg.text.lower()
    for row in get_filters():
        if row["keyword"] in text:
            try:
                await msg.delete()
                if row["response"]:
                    await context.bot.send_message(chat.id, row["response"])
                add_log(0, "filter_match", update.effective_user.id if update.effective_user else None,
                        f"keyword={row['keyword']}; chat={chat.id}")
            except Exception:
                pass
            break

# --- Fun group features: couples and mini puzzle games ---
PUZZLE_BANK = {
    "hidden": [
        ("R_SE", "rose"), ("L_VE", "love"), ("P_ZZLE", "puzzle"),
        ("T_LEGRAM", "telegram"), ("FR_END", "friend"), ("H_PPY", "happy"),
        ("S_NSHINE", "sunshine"), ("C_UPLE", "couple"),
    ],
    "scramble": [
        ("ESOR", "rose"), ("EVOL", "love"), ("ZZPUEL", "puzzle"),
        ("DNEIRF", "friend"), ("YPPHA", "happy"), ("EPOELP", "people"),
    ],
    "riddle": [
        ("I have keys but no locks, and space but no room. What am I?", "keyboard"),
        ("What has a face and two hands but no arms or legs?", "clock"),
        ("What gets wetter the more it dries?", "towel"),
        ("What has to be broken before you can use it?", "egg"),
        ("What has one eye but cannot see?", "needle"),
    ],
    "emoji": [
        ("🌹 + ❤️", "love"), ("🐝 + 🍯", "honey"), ("🌞 + 🌻", "sunflower"),
        ("📚 + 🐛", "bookworm"), ("🌧️ + 🌈", "rainbow"), ("🍎 + 📱", "apple"),
    ],
    "anagram": [("NIPAO", "piano"), ("RTAES", "tears"), ("HPEAL", "alpha"),
                 ("NOLME", "lemon"), ("RBAIN", "brain"), ("RSEOT", "store"),
                 ("TCAH", "chat"), ("NIGK", "king")],
    "trivia": [("Which planet is called the Red Planet?", "mars"),
               ("How many days are in a leap year?", "366"),
               ("What is the largest ocean on Earth?", "pacific"),
               ("Which animal is known as the king of the jungle?", "lion"),
               ("How many sides does a hexagon have?", "6")],
    "truefalse": [("A group of lions is called a pride. (true/false)", "true"),
                  ("The Sun is a planet. (true/false)", "false"),
                  ("Water freezes at 0°C at standard pressure. (true/false)", "true"),
                  ("Spiders have six legs. (true/false)", "false")],
}


def puzzle_help_text():
    return ("🧩 Nexus Bot Puzzle Games\n"
            "/hidden — guess the missing-letter word\n"
            "/scramble — unscramble the word\n"
            "/riddle — solve a riddle\n"
            "/emojiquiz — guess the emoji word\n"
            "/mathquiz — solve a quick math question\n"
            "/anagram — rearrange letters\n/wordle — guess the hidden word\n/hangman — guess a word\n/wordchain — continue the word chain\n"
            "/guessnumber — guess a number\n/fasttype — type the shown word\n/truefalse — quick true/false quiz\n/trivia — general knowledge\n"
            "/puzzlehelp — show these games\n"
            "First correct answer wins. Games run in groups.")

async def start_puzzle(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str):
    if not await dm_game_gate(update, context):
        return
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Please use puzzle games inside a group.")
        return
    if kind in ("hidden", "scramble", "emoji", "anagram", "trivia", "truefalse"):
        bank_key = {"scramble": "scramble", "emoji": "emoji", "anagram": "anagram", "trivia": "trivia", "truefalse": "truefalse"}.get(kind, "hidden")
        prompt, answer = random.choice(PUZZLE_BANK[bank_key])
    elif kind in ("wordle", "hangman", "wordchain", "fasttype"):
        word = random.choice(["planet", "garden", "friend", "silver", "orange", "puzzle", "rocket", "flower", "bridge", "castle"])
        if kind == "wordle":
            word = random.choice(["apple", "grape", "lemon", "plant", "smile", "heart", "dream", "brave"])
            prompt, answer = f"Guess the 5-letter word. Hint: it has {len(set(word))} unique letters. (This is a chat word-guess round; type the full word)", word
        elif kind == "hangman":
            prompt, answer = f"Hangman-style word: {' '.join('_' for _ in word)} ({len(word)} letters). Guess the whole word!", word
        elif kind == "wordchain":
            prompt, answer = "Word chain: name an English word that starts with the letter R.", "rose"
        else:
            prompt, answer = f"⚡ FAST TYPE: type this word exactly: {word}", word
    elif kind == "guessnumber":
        answer = str(random.randint(1, 50))
        prompt = "🔢 Guess a number from 1 to 50. First exact answer wins."
    elif kind == "math":
        a, b = random.randint(2, 30), random.randint(2, 20)
        operation = random.choice(("+", "-", "×"))
        if operation == "+": answer = str(a + b)
        elif operation == "-":
            if b > a: a, b = b, a
            answer = str(a - b)
        else: answer = str(a * b)
        prompt = f"{a} {operation} {b} = ?"
    else:
        prompt, answer = random.choice(PUZZLE_BANK["riddle"])
    ACTIVE_PUZZLES[chat.id] = {"answer": answer.casefold(), "kind": kind, "started": time.time()}
    labels = {"hidden": "🔤 Hidden Letter", "scramble": "🔀 Word Scramble", "riddle": "🧠 Riddle", "emoji": "🎭 Emoji Puzzle", "math": "➗ Math Challenge", "anagram": "🔠 Anagram", "wordle": "🟩 Word Guess", "hangman": "🪢 Hangman Word", "wordchain": "🔗 Word Chain", "guessnumber": "🔢 Guess Number", "fasttype": "⚡ Fast Type", "truefalse": "✅ True or False", "trivia": "🌍 Trivia Quiz"}
    await msg.reply_text(f"{labels[kind]}\n\n{prompt}\n\nReply in chat with your answer!")

async def hidden_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "hidden")

async def scramble_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "scramble")

async def riddle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "riddle")

async def emojiquiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "emoji")

async def mathquiz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "math")

async def anagram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "anagram")

async def wordle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "wordle")

async def hangman_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "hangman")

async def wordchain_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "wordchain")

async def guessnumber_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "guessnumber")

async def fasttype_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "fasttype")

async def truefalse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "truefalse")

async def trivia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_puzzle(update, context, "trivia")

async def puzzlehelp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await dm_game_gate(update, context):
        return
    await safe_reply(update, puzzle_help_text())

async def set_couple_image_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not actor_is_owner(update):
        await safe_reply(update, "⛔ Only the bot owner can change the couple image.")
        return
    msg = update.effective_message
    replied = msg.reply_to_message if msg else None
    if not replied or not replied.photo:
        await safe_reply(update, "Reply to a photo with /setcoupleimage to save it as the couple image.")
        return
    # Telegram file IDs are stable for reuse by this bot; store the largest photo size.
    set_setting("couple_image_file_id", replied.photo[-1].file_id)
    await safe_reply(update, "🌹 Couple image saved. Use /couple to test it.")

async def couple_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await dm_game_gate(update, context):
        return
    msg = update.effective_message
    chat = update.effective_chat
    if not msg or not chat or chat.type not in ("group", "supergroup"):
        await safe_reply(update, "Use /couple in a group.")
        return
    await tracked(update)

    # Replying to a member intentionally creates a fresh pair with that member.
    replied_user = msg.reply_to_message.from_user if msg.reply_to_message else None
    force_new = bool(replied_user)
    settings = get_settings()
    key = f"couple_last:{chat.id}"
    now = time.time()
    try:
        last = float(settings.get(key, "0"))
    except (TypeError, ValueError):
        last = 0
    if not force_new and now - last < COUPLE_COOLDOWN_SECONDS:
        remaining = int(COUPLE_COOLDOWN_SECONDS - (now - last))
        hours, rem = divmod(remaining, 3600)
        minutes = rem // 60
        await msg.reply_text(f"💞 A new group couple is available every 6 hours. Try again in {hours}h {minutes}m, or reply to a member's message with /couple to make a fresh pair.")
        return

    # Prefer users seen in the group/chat where possible; Telegram does not expose a full member list.
    candidates = []
    if replied_user:
        upsert_user(replied_user.id, replied_user.username, replied_user.first_name)
        upsert_group_user(chat.id, replied_user.id, replied_user.username, replied_user.first_name)
        candidates.append({"user_id": replied_user.id, "first_name": replied_user.first_name or replied_user.username or str(replied_user.id)})
    for row in list_group_users(chat.id, 500):
        if int(row["user_id"]) not in {c["user_id"] for c in candidates}:
            candidates.append({"user_id": int(row["user_id"]), "first_name": row.get("first_name") or ("@" + row["username"] if row.get("username") else str(row["user_id"]))})
    candidates = [c for c in candidates if c["user_id"] != getattr(context.bot, "id", None)]
    if len(candidates) < 2:
        await msg.reply_text("💞 I need at least two known group members. Ask members to send a message, then try /couple again.")
        return
    if replied_user:
        possible = [c for c in candidates if c["user_id"] != replied_user.id]
        if not possible:
            await msg.reply_text("I need one more known member to make a couple.")
            return
        first = candidates[0]
        second = random.choice(possible)
    else:
        first, second = random.sample(candidates, 2)
    set_setting(key, str(now))
    caption = (f"💘 Today's Nexus Bot Couple 💘\n\n"
               f"🌹 {first['first_name']}  ❤️  {second['first_name']} 🌹\n\n"
               f"Compatibility: {random.randint(60, 100)}% ✨")
    image_id = get_settings().get("couple_image_file_id", "").strip()
    try:
        if image_id:
            await context.bot.send_photo(chat_id=chat.id, photo=image_id, caption=caption)
        else:
            await msg.reply_text(caption + "\n\nOwner: reply to a photo with /setcoupleimage to add the couple image.")
    except Exception:
        await msg.reply_text(caption + "\n\n(Couple image could not be loaded.)")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    # Do not log secrets or full update payloads.
    print(f"Bot handler error: {type(context.error).__name__}")

def build_bot():
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", command_start))
    bot_app.add_handler(CommandHandler("help", help_cmd))
    bot_app.add_handler(CommandHandler("ping", ping_cmd))
    bot_app.add_handler(CommandHandler("points", points_cmd))
    bot_app.add_handler(CommandHandler("top", top_cmd))
    bot_app.add_handler(CommandHandler("auratop", auratop_cmd))
    bot_app.add_handler(CommandHandler("protect", protect_cmd))
    bot_app.add_handler(CommandHandler("giveaura", giveaura_cmd))
    bot_app.add_handler(CommandHandler("approve", approval_cmd))
    bot_app.add_handler(CommandHandler("decline", approval_cmd))
    bot_app.add_handler(CommandHandler("rob", rob_cmd))
    bot_app.add_handler(CommandHandler("id", id_cmd))
    bot_app.add_handler(CommandHandler("info", info_cmd))
    bot_app.add_handler(CommandHandler("history", history_cmd))
    bot_app.add_handler(CommandHandler("antispam", antispam_cmd))
    bot_app.add_handler(CommandHandler("free", free_cmd))
    bot_app.add_handler(CommandHandler("unfree", unfree_cmd))
    bot_app.add_handler(CommandHandler("translate", translate_cmd))
    bot_app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    bot_app.add_handler(CommandHandler("broadcast_at", broadcast_at_cmd))
    bot_app.add_handler(CommandHandler("ban", ban_cmd))
    bot_app.add_handler(CommandHandler("unban", unban_cmd))
    bot_app.add_handler(CommandHandler("mute", mute_cmd))
    bot_app.add_handler(CommandHandler("unmute", unmute_cmd))
    bot_app.add_handler(CommandHandler("filter", filter_cmd))
    bot_app.add_handler(CommandHandler("filters", filters_cmd))
    bot_app.add_handler(CommandHandler("couple", couple_cmd))
    bot_app.add_handler(CommandHandler("setcoupleimage", set_couple_image_cmd))
    bot_app.add_handler(CommandHandler("hidden", hidden_cmd))
    bot_app.add_handler(CommandHandler("scramble", scramble_cmd))
    bot_app.add_handler(CommandHandler("anagram", anagram_cmd))
    bot_app.add_handler(CommandHandler("wordle", wordle_cmd))
    bot_app.add_handler(CommandHandler("hangman", hangman_cmd))
    bot_app.add_handler(CommandHandler("wordchain", wordchain_cmd))
    bot_app.add_handler(CommandHandler("guessnumber", guessnumber_cmd))
    bot_app.add_handler(CommandHandler("fasttype", fasttype_cmd))
    bot_app.add_handler(CommandHandler("truefalse", truefalse_cmd))
    bot_app.add_handler(CommandHandler("trivia", trivia_cmd))
    bot_app.add_handler(CommandHandler("riddle", riddle_cmd))
    bot_app.add_handler(CommandHandler("emojiquiz", emojiquiz_cmd))
    bot_app.add_handler(CommandHandler("mathquiz", mathquiz_cmd))
    bot_app.add_handler(CommandHandler("puzzlehelp", puzzlehelp_cmd))
    bot_app.add_handler(ChatJoinRequestHandler(join_request))
    bot_app.add_handler(CallbackQueryHandler(join_request_action, pattern=r"^jr:(approve|decline):-?\d+:\d+$"))
    bot_app.add_handler(CallbackQueryHandler(start_buttons_callback, pattern=r"^start:(help|ping)$"))
    bot_app.add_handler(MessageHandler((filters.ALL & ~filters.COMMAND), on_message))
    bot_app.add_error_handler(error_handler)
    return bot_app

async def run_bot():
    bot_app = build_bot()
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

if __name__ == "__main__":
    async def main():
        task = asyncio.create_task(run_bot())
        from threading import Thread
        Thread(target=lambda: serve(app, host="0.0.0.0", port=PORT, threads=8), daemon=True).start()
        await task
    asyncio.run(main())
