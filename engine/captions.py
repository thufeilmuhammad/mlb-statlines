import datetime

def get_today_formatted():
    return datetime.date.today().strftime('%B %d, %Y')

# ══════════════════════════════════════
# TEMPLATE STRINGS PER STORY TYPE
# ══════════════════════════════════════

def write_pace_caption(story):
    name = story['entity_name']
    stat = story['stat_label']
    current = story['value']
    projected = story['projected']
    games = story['games_played']
    record = story['record']

    hook = f"{name} is on pace for {projected} {stat} this season."
    context = f"{current} {stat} through {games} games."
    rarity = f"The single-season record is {record}."
    cta = f"Is this the real deal? 👇"
    hashtags = f"#MLB #Baseball #{name.replace(' ', '')} #FullCount"

    caption = f"{hook}\n\n{context} {rarity}\n\n{cta}\n\n{hashtags}"
    return caption

def write_streak_caption(story):
    name = story['entity_name']
    value = story['value']
    stat_type = 'hitting' if story['type'] == 'hitting_streak' else 'on-base'

    hook = f"{name} has a {value}-game {stat_type} streak."
    context = f"That's one of the longest active {stat_type} streaks in baseball right now."
    cta = f"How far does it go? 👇"
    hashtags = f"#MLB #Baseball #{name.replace(' ', '')} #FullCount"

    caption = f"{hook}\n\n{context}\n\n{cta}\n\n{hashtags}"
    return caption

def write_outlier_caption(story):
    name = story['entity_name']
    value = story['value']
    stat = story['stat'].upper()
    z = story['z_score']

    if story['type'] == 'outlier_era':
        hook = f"{name} has a {value} ERA this season."
        context = f"That puts him in the top tier of all MLB starters — {z} standard deviations better than average."
    else:
        hook = f"{name} is posting a {value} {stat} this season."
        context = f"That's {z} standard deviations above the MLB average — elite territory."

    cta = f"The numbers don't lie. 👇"
    hashtags = f"#MLB #Baseball #Statcast #{name.replace(' ', '')} #FullCount"

    caption = f"{hook}\n\n{context}\n\n{cta}\n\n{hashtags}"
    return caption

# ══════════════════════════════════════
# MASTER CAPTION WRITER
# ══════════════════════════════════════

def write_caption(story):
    story_type = story['type']
    if story_type == 'pace':
        return write_pace_caption(story)
    elif story_type in ['hitting_streak', 'onbase_streak']:
        return write_streak_caption(story)
    elif story_type in ['outlier_ops', 'outlier_avg', 'outlier_era']:
        return write_outlier_caption(story)
    else:
        return f"{story['entity_name']} — {story['label']} #MLB #FullCount"

# ══════════════════════════════════════
# GENERATE DIGEST FOR TELEGRAM
# ══════════════════════════════════════

def generate_digest(top_stories):
    today = get_today_formatted()
    lines = [f"FULL COUNT · {today}", f"Today's top stories:\n"]
    for i, story in enumerate(top_stories, 1):
        caption_preview = write_caption(story).split('\n')[0]
        lines.append(
            f"{i}. {story['entity_name']} [{story['final_score']}]\n"
            f"   {story['label']}\n"
            f"   {caption_preview}\n"
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