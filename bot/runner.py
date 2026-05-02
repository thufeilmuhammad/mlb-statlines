"""
GitHub Actions-compatible runner.

Sends the morning story digest via Telegram, then polls for the editor's
reply (pick → review → OK/skip/edit).  When a post is approved it copies
the rendered graphic to data/approved_image.png, updates
data/approved_post.json, and commits both back to the repo so the 11am
Instagram-post workflow can read them.

Exits after approval or after a 4-hour timeout.
"""

import asyncio
import datetime
import json
import os
import shutil
import subprocess
import time

from dotenv import load_dotenv

load_dotenv()

APPROVED_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'approved_post.json')
)
APPROVED_IMAGE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'approved_image.png')
)


def _commit_approved():
    """Copy graphic to stable path, update JSON, push to repo."""
    with open(APPROVED_FILE) as f:
        post = json.load(f)

    src = post.get('image_path', '')
    if src and not os.path.isabs(src):
        src = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', src))

    if src and os.path.exists(src) and os.path.abspath(src) != os.path.abspath(APPROVED_IMAGE):
        shutil.copy2(src, APPROVED_IMAGE)

    if os.path.exists(APPROVED_IMAGE):
        post['image_path'] = 'data/approved_image.png'
        with open(APPROVED_FILE, 'w') as f:
            json.dump(post, f, indent=2)
    else:
        print(f"Warning: image not found at {src}")

    subprocess.run(['git', 'add', 'data/approved_post.json', 'data/approved_image.png'], check=True)
    staged = subprocess.run(['git', 'diff', '--staged', '--quiet'])
    if staged.returncode != 0:
        today = datetime.date.today().isoformat()
        subprocess.run(['git', 'commit', '-m', f'chore: approved post {today}'], check=True)
        subprocess.run(['git', 'push'], check=True)
        print("Committed and pushed approved post.")
    else:
        print("Nothing new to commit.")


async def main():
    import telegram
    from engine.detectors import run_all_detectors
    from engine.scorer import rank_candidates
    from bot.approval_flow import save_state, route_reply_async

    TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
    CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

    # Remove stale approved post from a previous day
    if os.path.exists(APPROVED_FILE):
        with open(APPROVED_FILE) as f:
            old = json.load(f)
        if not old.get('approved_at', '').startswith(datetime.date.today().isoformat()):
            os.remove(APPROVED_FILE)
            print("Removed stale approved_post.json from a previous day.")

    bot = telegram.Bot(token=TOKEN)

    # ── Run story engine ──
    print("Running story engine...")
    candidates = run_all_detectors()
    top        = rank_candidates(candidates, top_n=5)

    if not top:
        await bot.send_message(chat_id=CHAT_ID, text="No strong story candidates today.")
        print("No candidates — exiting.")
        return

    # Save state so approval_flow handlers can look up stories
    state = {
        'step': 'awaiting_pick',
        'stories': [
            {k: v for k, v in s.items() if isinstance(v, (str, int, float, bool, type(None)))}
            for s in top
        ],
        'date': datetime.date.today().strftime('%Y-%m-%d'),
    }
    save_state(state)

    # ── Send digest ──
    today_str = datetime.date.today().strftime('%B %d, %Y')
    lines = [f"<b>FULL COUNT · {today_str}</b>", "Today's top stories:\n"]
    for i, story in enumerate(top, 1):
        lines.append(
            f"{i}. <b>{story['entity_name']}</b> [{story['final_score']}]\n"
            f"   {story['label']}\n"
        )
    lines.append("Reply with a number (1–5) to pick a story.")
    await bot.send_message(chat_id=CHAT_ID, text='\n'.join(lines), parse_mode='HTML')
    print(f"Digest sent — {len(top)} stories.")

    # ── Poll for replies (4-hour window) ──
    updates = await bot.get_updates(timeout=0)
    offset  = (max(u.update_id for u in updates) + 1) if updates else 0

    deadline = time.time() + 4 * 3600
    print(f"Listening until {datetime.datetime.fromtimestamp(deadline).strftime('%H:%M UTC')} ...")

    while time.time() < deadline:
        # Check for approval written by handle_review → log_approved
        if os.path.exists(APPROVED_FILE):
            with open(APPROVED_FILE) as f:
                post = json.load(f)
            if post.get('approved_at'):
                print("Post approved — committing to repo...")
                _commit_approved()
                return

        try:
            updates = await bot.get_updates(
                offset=offset, timeout=30, allowed_updates=['message']
            )
            for update in updates:
                offset = update.update_id + 1
                if update.message and update.message.text:
                    text    = update.message.text.strip()
                    chat_id = str(update.message.chat.id)
                    print(f"Message [{chat_id}]: {text}")
                    await route_reply_async(text, bot, chat_id)
        except Exception as e:
            print(f"Poll error: {e}")
            await asyncio.sleep(5)

    print("4-hour window expired without approval.")
    await bot.send_message(
        chat_id=CHAT_ID,
        text="No post approved today — session expired. Nothing will be posted at 11am.",
    )


if __name__ == '__main__':
    asyncio.run(main())
