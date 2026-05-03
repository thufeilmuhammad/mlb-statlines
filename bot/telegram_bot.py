import os
import asyncio
import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

async def send_message(text):
    import telegram
    bot = telegram.Bot(token=TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')

async def send_photo(image_path, caption=None):
    import telegram
    bot = telegram.Bot(token=TOKEN)
    with open(image_path, 'rb') as f:
        await bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption)

def send(text):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_message(text))
    except RuntimeError:
        asyncio.run(send_message(text))

def send_image(image_path, caption=None):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_photo(image_path, caption))
    except RuntimeError:
        asyncio.run(send_photo(image_path, caption))

def send_digest(top_stories):
    from engine.context import build_digest_context
    type_tag = {
        'hitting_streak': 'HIT STREAK',
        'onbase_streak':  'OBP STREAK',
        'pace':           'PACE',
        'outlier_ops':    'OPS',
        'outlier_avg':    'AVG',
        'outlier_era':    'ERA',
        'cold_streak':    'COLD',
        'era_spike':      'SPIKE',
    }
    today = datetime.date.today().strftime('%B %d, %Y')
    lines = [f"<b>FULL COUNT · {today}</b>", "Today's top stories:\n"]
    for i, story in enumerate(top_stories, 1):
        tag     = type_tag.get(story['type'], story['type'].upper())
        team    = story.get('team', '')
        meta    = f"{team} · {tag}" if team else tag
        context = build_digest_context(story)
        entry   = (
            f"{i}. <b>{story['entity_name']}</b> · {meta} — {story['final_score']}\n"
            f"   {story['label']}\n"
        )
        if context:
            entry += f"   <i>{context}</i>\n"
        lines.append(entry)
    lines.append(f"Reply with a number (1–{len(top_stories)}) to pick a story.")
    text = '\n'.join(lines)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_message(text))
    except RuntimeError:
        asyncio.run(send_message(text))

def send_graphic_for_review(image_path, story, caption):
    review_text = (
        f"<b>Story #{story.get('pick_number', 1)}</b>\n\n"
        f"<b>Caption draft:</b>\n{caption}\n\n"
        f"Reply:\n"
        f"<b>OK</b> — post as is\n"
        f"<b>E [text]</b> — edit caption\n"
        f"<b>R</b> — regenerate same\n"
        f"<b>R LINECHART</b> — change chart type\n"
        f"<b>R [instruction]</b> — regenerate with change\n"
        f"<b>S</b> — skip, see next story"
    )
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_photo(image_path, review_text[:1024]))
    except RuntimeError:
        asyncio.run(send_photo(image_path, review_text[:1024]))

def start_listener(on_message_callback):
    from telegram.ext import ApplicationBuilder, MessageHandler, filters
    app = ApplicationBuilder().token(TOKEN).build()
    async def handler(update, context):
        text = update.message.text.strip()
        await on_message_callback(text, update, context)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))
    print("Telegram bot listening...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    print("Sending test message...")
    asyncio.run(send_message("Full Count bot is connected. Ready to go."))
    print("Done — check your Telegram.")
