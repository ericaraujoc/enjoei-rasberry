import asyncio
import logging
import os
import time
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import runner
import stores as store_mgr

load_dotenv()

TOKEN = os.environ["TELEGRAM_TOKEN"]
OWNER_ID = int(os.environ["TELEGRAM_USER_ID"])

logging.basicConfig(
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────────────────
ADD_COOKIE, ADD_URL, ADD_NAME, ADD_INTERVAL = range(4)
REN_SELECT, REN_NEW = range(4, 6)
SETINT_SELECT, SETINT_NEW = range(6, 8)


# ── Auth decorator ────────────────────────────────────────────────────────────
def owner_only(func):
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, ctx)
    return wrapper


# ── /start ────────────────────────────────────────────────────────────────────
@owner_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🛒 *Enjoei Megafonar Bot*\n\n"
        "/addcookie — add a store\n"
        "/status — stores & today's stats\n"
        "/rename — rename a store\n"
        "/remove — remove a store\n"
        "/resume — today's summary\n"
        "/setinterval — change a store's run interval",
        parse_mode="Markdown",
    )


# ── /status ───────────────────────────────────────────────────────────────────
@owner_only
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    stores = store_mgr.all_stores()
    if not stores:
        await update.message.reply_text("No stores yet. Use /addcookie.")
        return

    now = time.time()
    lines = ["📊 *Store Status*\n"]
    for sid, s in stores.items():
        stats = store_mgr.today_stats(sid)
        last = s.get("last_boost")
        last_str = datetime.fromisoformat(last).strftime("%H:%M") if last else "never"
        next_run = s.get("next_run", 0)
        wait_sec = max(0, next_run - now)
        wait_str = f"{int(wait_sec // 60)}m {int(wait_sec % 60)}s" if wait_sec > 0 else "now"
        icon = "🟢" if s["active"] else "🔴"
        cookie_preview = s["cookie"][:20] + "..."
        lines.append(
            f"{icon} *{s['name']}*\n"
            f"   Interval: every {s.get('interval_minutes', 20)} min | next in: {wait_str}\n"
            f"   Last boost: {last_str}\n"
            f"   Today: {stats['total_boosts']} boosts / {stats['rounds']} rounds\n"
            f"   Cookie: `{cookie_preview}`\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── /resume ───────────────────────────────────────────────────────────────────
@owner_only
async def cmd_resume(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_resume(ctx.bot, update.effective_chat.id)


async def _send_resume(bot, chat_id: int) -> None:
    stores = store_mgr.all_stores()
    if not stores:
        return
    date_str = datetime.now().strftime("%d/%m/%Y")
    lines = [f"📈 *Daily Resume — {date_str}*\n"]
    total = 0
    for sid, s in stores.items():
        stats = store_mgr.today_stats(sid)
        boosts = stats["total_boosts"]
        rounds = stats["rounds"]
        total += boosts
        lines.append(f"• *{s['name']}* (every {s.get('interval_minutes', 20)} min): {boosts} boosts / {rounds} rounds")
    lines.append(f"\n*Total: {total} boosts today*")
    await bot.send_message(chat_id, "\n".join(lines), parse_mode="Markdown")


# ── /addcookie conversation ───────────────────────────────────────────────────
# Flow: cookie → interval → name → URL

@owner_only
async def cmd_addcookie(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "1/4 — Paste the `_website_session_7` cookie value:\n_(or /cancel to abort)_",
        parse_mode="Markdown",
    )
    return ADD_COOKIE


async def got_cookie(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["cookie"] = update.message.text.strip()
    await update.message.reply_text(
        "2/4 — Run interval in minutes? (e.g. `20`)", parse_mode="Markdown"
    )
    return ADD_INTERVAL


async def got_interval(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    if not raw.isdigit() or int(raw) < 5:
        await update.message.reply_text("Please enter a number ≥ 5.")
        return ADD_INTERVAL
    ctx.user_data["interval"] = int(raw)
    await update.message.reply_text(
        "3/4 — Custom name for this store? (e.g. `Loja Érica`)", parse_mode="Markdown"
    )
    return ADD_NAME


async def got_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "4/4 — Store handle on Enjoei? (e.g. `@ericshop`)", parse_mode="Markdown"
    )
    return ADD_URL


async def got_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    name = ctx.user_data["name"]
    interval = ctx.user_data["interval"]
    store_mgr.add_store(
        name=name,
        url=update.message.text.strip(),
        cookie=ctx.user_data["cookie"],
        interval_minutes=interval,
    )
    await update.message.reply_text(
        f"✅ *{name}* added — runs every *{interval} min*!", parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── /rename conversation ──────────────────────────────────────────────────────
@owner_only
async def cmd_rename(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    stores = store_mgr.all_stores()
    if not stores:
        await update.message.reply_text("No stores to rename.")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(s["name"], callback_data=sid)]
        for sid, s in stores.items()
    ]
    await update.message.reply_text(
        "Which store to rename?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return REN_SELECT


async def ren_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["rename_id"] = q.data
    store = store_mgr.get_store(q.data)
    await q.edit_message_text(
        f"New name for *{store['name']}*:", parse_mode="Markdown"
    )
    return REN_NEW


async def ren_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()
    store_mgr.rename_store(ctx.user_data["rename_id"], new_name)
    await update.message.reply_text(f"✅ Renamed to *{new_name}*.", parse_mode="Markdown")
    return ConversationHandler.END


# ── /setinterval conversation ─────────────────────────────────────────────────
@owner_only
async def cmd_setinterval(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    stores = store_mgr.all_stores()
    if not stores:
        await update.message.reply_text("No stores configured.")
        return ConversationHandler.END
    keyboard = [
        [InlineKeyboardButton(
            f"{s['name']} (now: {s.get('interval_minutes', 20)} min)",
            callback_data=sid,
        )]
        for sid, s in stores.items()
    ]
    await update.message.reply_text(
        "Which store's interval to change?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SETINT_SELECT


async def setint_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["setint_id"] = q.data
    store = store_mgr.get_store(q.data)
    current = store.get("interval_minutes", 20)
    await q.edit_message_text(
        f"*{store['name']}* — current interval: *{current} min*\n\nNew interval (minutes, min 5):",
        parse_mode="Markdown",
    )
    return SETINT_NEW


async def setint_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    if not raw.isdigit() or int(raw) < 5:
        await update.message.reply_text("Please enter a number ≥ 5.")
        return SETINT_NEW
    minutes = int(raw)
    sid = ctx.user_data["setint_id"]
    store = store_mgr.get_store(sid)
    store_mgr.set_store_interval(sid, minutes)
    await update.message.reply_text(
        f"✅ *{store['name']}* will now run every *{minutes} min*.", parse_mode="Markdown"
    )
    return ConversationHandler.END


# ── /remove ───────────────────────────────────────────────────────────────────
@owner_only
async def cmd_remove(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    stores = store_mgr.all_stores()
    if not stores:
        await update.message.reply_text("No stores to remove.")
        return
    keyboard = [
        [InlineKeyboardButton(f"🗑 {s['name']}", callback_data=f"rm_{sid}")]
        for sid, s in stores.items()
    ]
    await update.message.reply_text(
        "Which store to remove?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def remove_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    sid = q.data[3:]  # strip "rm_"
    store = store_mgr.get_store(sid)
    if store:
        store_mgr.remove_store(sid)
        await q.edit_message_text(f"🗑 *{store['name']}* removed.", parse_mode="Markdown")


# ── Scheduler ─────────────────────────────────────────────────────────────────
async def _scheduler(app: Application) -> None:
    resume_sent_today: str | None = None

    while True:
        now = time.time()
        stores = store_mgr.all_stores()

        for sid, s in stores.items():
            if not s.get("active"):
                continue
            if now < s.get("next_run", 0):
                continue  # not due yet

            logger.info(f"Running: {s['name']} (every {s.get('interval_minutes', 20)} min)")
            try:
                count = await runner.executar_megafonar(s["url"], s["cookie"])
                if count == -1:
                    await app.bot.send_message(
                        OWNER_ID,
                        f"⚠️ *{s['name']}*: cookie expired or not logged in.",
                        parse_mode="Markdown",
                    )
                else:
                    store_mgr.record_boost(sid, count)
                    interval = s.get("interval_minutes", 20)
                    store_mgr.set_next_run(sid, now + interval * 60)
                    logger.info(f"{s['name']}: {count} boosts — next in {interval} min")
            except Exception as e:
                logger.error(f"{s['name']} error: {e}")

        # Daily resume at 23:55 (once per day)
        dt = datetime.now()
        today = dt.strftime("%Y-%m-%d")
        if dt.hour == 23 and dt.minute >= 55 and resume_sent_today != today:
            await _send_resume(app.bot, OWNER_ID)
            resume_sent_today = today

        await asyncio.sleep(30)  # check every 30 seconds


async def _post_init(app: Application) -> None:
    asyncio.create_task(_scheduler(app))


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    app = Application.builder().token(TOKEN).post_init(_post_init).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("addcookie", cmd_addcookie)],
        states={
            ADD_COOKIE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, got_cookie)],
            ADD_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_interval)],
            ADD_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)],
            ADD_URL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, got_url)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    rename_conv = ConversationHandler(
        entry_points=[CommandHandler("rename", cmd_rename)],
        states={
            REN_SELECT: [CallbackQueryHandler(ren_selected)],
            REN_NEW:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ren_done)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    setint_conv = ConversationHandler(
        entry_points=[CommandHandler("setinterval", cmd_setinterval)],
        states={
            SETINT_SELECT: [CallbackQueryHandler(setint_selected)],
            SETINT_NEW:    [MessageHandler(filters.TEXT & ~filters.COMMAND, setint_done)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CallbackQueryHandler(remove_cb, pattern=r"^rm_"))
    app.add_handler(add_conv)
    app.add_handler(rename_conv)
    app.add_handler(setint_conv)

    app.run_polling()


if __name__ == "__main__":
    main()
