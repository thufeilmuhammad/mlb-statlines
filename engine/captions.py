import datetime

def get_today_formatted():
    return datetime.date.today().strftime('%B %d, %Y')

# ══════════════════════════════════════
# CAPTION WRITERS
# ══════════════════════════════════════

def write_pace_caption(story):
    name      = story['entity_name']
    stat      = story['stat_label']
    current   = story['value']
    projected = story['projected']
    games     = story['games_played']
    record    = story['record']
    ctx       = story.get('record_context', f'The single-season record is {record}.')

    hook     = story['label'] + '.'
    body     = f"{current} {stat} through {games} games. {ctx}"
    cta      = f"Is this the real deal? 👇"
    hashtags = f"#MLB #Baseball #{name.replace(' ', '')} #FullCountID"

    return f"{hook}\n\n{body}\n\n{cta}\n\n{hashtags}"

def write_streak_caption(story):
    name  = story['entity_name']
    value = story['value']
    kind  = 'hitting' if story['type'] == 'hitting_streak' else 'on-base'
    lede  = story.get('lede', '')

    hook     = story['label'] + '.'
    cta      = f"How far does it go? 👇"
    hashtags = f"#MLB #Baseball #{name.replace(' ', '')} #FullCountID"

    return f"{hook}\n\n{lede}\n\n{cta}\n\n{hashtags}"

def write_outlier_caption(story):
    name = story['entity_name']
    lede = story.get('lede', '')

    hook     = story['label'] + '.'
    cta      = "The numbers don't lie. 👇"
    hashtags = f"#MLB #Baseball #Statcast #{name.replace(' ', '')} #FullCountID"

    return f"{hook}\n\n{lede}\n\n{cta}\n\n{hashtags}"

def write_caption(story):
    t = story['type']
    if t == 'pace':
        return write_pace_caption(story)
    elif t in ['hitting_streak', 'onbase_streak']:
        return write_streak_caption(story)
    elif t in ['outlier_ops', 'outlier_avg', 'outlier_era']:
        return write_outlier_caption(story)
    return f"{story['entity_name']} — {story['label']} #MLB #FullCountID"

# ══════════════════════════════════════
# TELEGRAM DIGEST
# ══════════════════════════════════════

def generate_digest(top_stories):
    today = get_today_formatted()
    lines = [f"FULL COUNT · {today}", f"Today's top stories:\n"]
    for i, story in enumerate(top_stories, 1):
        lines.append(
            f"{i}. {story['entity_name']} [{story['final_score']}]\n"
            f"   {story['label']}\n"
        )
    lines.append("Reply 1–5 to pick a story.")
    return '\n'.join(lines)

if __name__ == '__main__':
    from engine.detectors import run_all_detectors
    from engine.scorer import rank_candidates
    candidates = run_all_detectors()
    top = rank_candidates(candidates)
    digest = generate_digest(top)
    print("\n=== TELEGRAM DIGEST PREVIEW ===\n")
    print(digest)
    print("\n=== CAPTION PREVIEW FOR STORY 1 ===\n")
    print(write_caption(top[0]))
