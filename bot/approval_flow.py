import os
import json
import datetime
import asyncio
from dotenv import load_dotenv
from engine.detectors import run_all_detectors
from engine.scorer import rank_candidates
from engine.captions import write_caption, generate_digest
from templates.render import render_story
from data.database import get_connection

load_dotenv()

STATE_FILE    = os.path.join(os.path.dirname(__file__), '..', 'data', 'approval_state.json')
APPROVED_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'approved_post.json')

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def clear_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def log_approved(story, caption, image_path):
    conn = get_connection()
    c    = conn.cursor()
    today = datetime.date.today().strftime('%Y-%m-%d')
    c.execute('''
        INSERT INTO story_log
        (story_type, entity_id, entity_name, score, headline, posted, posted_date, created_date)
        VALUES (?,?,?,?,?,?,?,?)
    ''', (
        story.get('type', ''),
        str(story.get('entity_id', '')),
        story.get('entity_name', ''),
        story.get('final_score', 0),
        story.get('label', ''),
        1, today, today
    ))
    conn.commit()
    conn.close()
    approved = {
        'image_path': image_path,
        'caption':    caption,
        'story':      story,
        'approved_at': datetime.datetime.now().isoformat()
    }
    with open(APPROVED_FILE, 'w') as f:
        json.dump(approved, f)
    print(f"Approved post saved.")

def run_morning_digest():
    from bot.telegram_bot import send_digest, send_message
    print("Running story engine...")
    candidates = run_all_detectors()
    top        = rank_candidates(candidates, top_n=10)
    if not top:
        asyncio.run(send_message("No strong story candidates today."))
        return
    state = {
        'step': 'awaiting_pick',
        'stories': [
            {k: v for k, v in s.items() if isinstance(v, (str, int, float, bool, type(None)))}
            for s in top
        ],
        'date': datetime.date.today().strftime('%Y-%m-%d')
    }
    save_state(state)
    send_digest(top)
    print(f"Digest sent — {len(top)} stories.")

def get_full_story(story):
    candidates = run_all_detectors()
    full = next(
        (c for c in candidates
         if str(c.get('entity_id')) == str(story.get('entity_id'))
         and c.get('type') == story.get('type')
         and c.get('stat', '') == story.get('stat', '')),
        story
    )
    return full

async def handle_pick(pick_number, bot, chat_id):
    state   = load_state()
    stories = state.get('stories', [])
    idx     = pick_number - 1

    if idx < 0 or idx >= len(stories):
        await bot.send_message(chat_id=chat_id, text=f"Invalid. Reply 1-{len(stories)}.")
        return

    story = stories[idx]
    story['pick_number'] = pick_number
    await bot.send_message(chat_id=chat_id, text=f"Generating graphic for story {pick_number}...")

    full_story = get_full_story(story)
    full_story['pick_number'] = pick_number

    image_path = render_story(full_story)
    caption    = write_caption(full_story)

    state['step']       = 'awaiting_review'
    state['story']      = {k: v for k, v in full_story.items() if isinstance(v, (str, int, float, bool, type(None)))}
    state['caption']    = caption
    state['image_path'] = image_path
    save_state(state)

    review_text = (
        f"<b>Story #{pick_number}</b>\n\n"
        f"<b>Caption draft:</b>\n{caption}\n\n"
        f"Reply:\n"
        f"<b>OK</b> — post as is\n"
        f"<b>E [text]</b> — edit caption\n"
        f"<b>R</b> — regenerate same\n"
        f"<b>R [instruction]</b> — change something\n"
        f"<b>S</b> — skip"
    )
    with open(image_path, 'rb') as f:
        await bot.send_photo(chat_id=chat_id, photo=f, caption=review_text[:1024], parse_mode='HTML')

async def handle_review(reply_text, bot, chat_id):
    state  = load_state()
    story  = state.get('story', {})
    reply  = reply_text.strip().upper()

    if reply == 'OK':
        caption    = state.get('caption', '')
        image_path = state.get('image_path', '')
        log_approved(story, caption, image_path)
        await bot.send_message(chat_id=chat_id, text="Approved. Post scheduled for 11am.", parse_mode='HTML')
        clear_state()

    elif reply == 'S':
        await bot.send_message(chat_id=chat_id, text="Skipped. Reply with a number to pick another story.")
        state['step'] = 'awaiting_pick'
        save_state(state)

    elif reply_text.strip().upper().startswith('E '):
        new_caption = reply_text.strip()[2:].strip()
        state['caption'] = new_caption
        save_state(state)
        await bot.send_message(chat_id=chat_id, text=f"Caption updated:\n\n{new_caption}\n\nReply OK to post or R to regenerate.", parse_mode='HTML')

    elif reply == 'R':
        await bot.send_message(chat_id=chat_id, text="Regenerating...")
        full_story = get_full_story(story)
        image_path = render_story(full_story)
        caption    = write_caption(full_story)
        state['image_path'] = image_path
        state['caption']    = caption
        state['story']      = {k: v for k, v in full_story.items() if isinstance(v, (str, int, float, bool, type(None)))}
        save_state(state)
        review_text = f"<b>Regenerated</b>\n\n<b>Caption:</b>\n{caption}\n\nReply OK, E [text], R, or S."
        with open(image_path, 'rb') as f:
            await bot.send_photo(chat_id=chat_id, photo=f, caption=review_text[:1024], parse_mode='HTML')

    elif reply_text.strip().upper().startswith('R '):
        instruction = reply_text.strip()[2:].strip()
        await bot.send_message(chat_id=chat_id, text=f"Regenerating with: {instruction}")
        full_story = get_full_story(story)
        instruction_upper = instruction.upper()
        if instruction_upper == 'LINECHART':
            full_story['chart_type'] = 'line'
        elif instruction_upper == 'BARCHART':
            full_story['chart_type'] = 'bar'
        image_path = render_story(full_story)
        caption    = write_caption(full_story)
        state['image_path'] = image_path
        state['caption']    = caption
        state['story']      = {k: v for k, v in full_story.items() if isinstance(v, (str, int, float, bool, type(None)))}
        save_state(state)
        review_text = f"<b>Regenerated</b>\n\n<b>Caption:</b>\n{caption}\n\nReply OK, E [text], R, or S."
        with open(image_path, 'rb') as f:
            await bot.send_photo(chat_id=chat_id, photo=f, caption=review_text[:1024], parse_mode='HTML')

    else:
        await bot.send_message(chat_id=chat_id, text="Didn't understand. Reply OK, S, E [text], R, or R [instruction].")

async def route_reply_async(text, bot, chat_id):
    state = load_state()
    step  = state.get('step', '')
    if step == 'awaiting_pick':
        n = len(state.get('stories', []))
        if text.strip().isdigit() and 1 <= int(text.strip()) <= n:
            await handle_pick(int(text.strip()), bot, chat_id)
        else:
            await bot.send_message(chat_id=chat_id, text=f"Reply with a number (1–{n}) to pick a story.")
    elif step == 'awaiting_review':
        await handle_review(text, bot, chat_id)
    else:
        await bot.send_message(chat_id=chat_id, text="No active session. Morning digest runs at 6am.")

if __name__ == '__main__':
    run_morning_digest()
