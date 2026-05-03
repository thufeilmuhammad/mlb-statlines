import datetime

def get_today_formatted():
    return datetime.date.today().strftime('%B %d, %Y')

# ══════════════════════════════════════
# HISTORICAL THRESHOLD NOTES
# Applied when projected/current value crosses a known milestone.
# ══════════════════════════════════════

_HR_NOTES = [
    (73, "Only Barry Bonds (73, 2001) has ever hit more in a single season."),
    (62, "Only Roger Maris (61, 1961) and Barry Bonds (73, 2001) have ever hit more in a single season."),
    (60, "Only 4 players in MLB history have hit 60 or more home runs in a season."),
    (55, "Fewer than 10 seasons in MLB history have seen a player reach 55 HR."),
    (50, "The 50 HR club is one of baseball's most exclusive — fewer than 30 times in history."),
]

_RBI_NOTES = [
    (190, "The all-time single-season RBI record is 191, set by Hack Wilson in 1930."),
    (170, "Only a handful of seasons in baseball history have reached 170+ RBI."),
    (150, "150 RBI in a season hasn't been done since the early 2000s."),
    (130, "130 RBI is an elite total — a pace that would lead the league most seasons."),
]

_HIT_NOTES = [
    (257, "The all-time record of 257 hits, set by Ichiro in 2004, is considered untouchable."),
    (230, "230+ hits in a season is exceptionally rare in modern baseball."),
    (210, "200 hits in a season is a benchmark fewer than 20 players reach per decade."),
]

_SB_NOTES = [
    (130, "Rickey Henderson's all-time record of 130 stolen bases (1982) has stood for over 40 years."),
    (100, "100 stolen bases in a season is a threshold only Rickey Henderson and Vince Coleman have crossed."),
    (80, "80 stolen bases would rank among the greatest single-season totals ever."),
    (60, "60 stolen bases in a season is elite — only a handful of players reach it each decade."),
]

_OPS_NOTES = [
    (1.400, "An OPS above 1.400 is historically unprecedented for a full season."),
    (1.200, "An OPS above 1.200 is Bonds-level — among the greatest offensive seasons ever."),
    (1.100, "An OPS above 1.100 is historically elite — fewer than 5 players sustain it in any given decade."),
    (1.000, "An OPS above 1.000 is the mark of an MVP-caliber offensive season."),
]

_AVG_NOTES = [
    (0.400, "No player has batted .400 for a full season since Ted Williams in 1941."),
    (0.380, "A .380 average would be the highest single-season mark since Tony Gwynn (.394) in 1994."),
    (0.360, "A .360+ average puts this player among the greatest contact hitters in a generation."),
    (0.340, "A .340 average is elite in the modern era — a number that leads the league most seasons."),
]

_ERA_NOTES = [
    (1.00, "An ERA below 1.00 sustained over a full season has never been done in the modern era."),
    (1.50, "A sub-1.50 ERA over a full season is historically exceptional — Walter Johnson territory."),
    (2.00, "A sub-2.00 ERA sustained over a full season is exceedingly rare in the modern game."),
    (2.50, "A sub-2.50 ERA is elite by any era's standards."),
]

_THRESHOLD_MAP = {
    'hr':   (_HR_NOTES,  True),
    'rbi':  (_RBI_NOTES, True),
    'hits': (_HIT_NOTES, True),
    'sb':   (_SB_NOTES,  True),
    'ops':  (_OPS_NOTES, True),
    'avg':  (_AVG_NOTES, True),
    'era':  (_ERA_NOTES, False),
}

def _historical_note(stat, value):
    """Return the most relevant historical note for a stat value, or ''."""
    entry = _THRESHOLD_MAP.get(stat)
    if not entry:
        return ''
    thresholds, higher_is_better = entry
    for threshold, note in thresholds:
        if higher_is_better and value >= threshold:
            return note
        if not higher_is_better and value <= threshold:
            return note
    return ''


# ══════════════════════════════════════
# CAREER HIGH HELPERS
# ══════════════════════════════════════

def _career_line_batting(player_id, stat_col, current_val, label, higher_is_better=True):
    """Return a one-sentence career-high line, or '' if no history."""
    try:
        from engine.context import career_batting
        best_val, best_yr = career_batting(player_id, stat_col, higher_is_better)
        if best_val is None:
            return ''
        if higher_is_better:
            if current_val is not None and current_val > best_val:
                return f"His career best before this season was {best_val} {label} ({best_yr}) — he's already tracking above that."
            return f"His career best is {best_val} {label} ({best_yr})."
        else:
            if current_val is not None and current_val < best_val:
                return f"His career best ERA before this season was {best_val} ({best_yr}) — he's tracking below that now."
            return f"His career best ERA is {best_val} ({best_yr})."
    except Exception:
        return ''


def _career_line_pitching(player_id, stat_col, current_val, label):
    try:
        from engine.context import career_pitching
        best_val, best_yr = career_pitching(player_id, stat_col, higher_is_better=False)
        if best_val is None:
            return ''
        if current_val is not None and current_val < best_val:
            return f"His career best ERA before this season was {best_val} ({best_yr}) — he's tracking below that now."
        return f"His career best ERA is {best_val} ({best_yr})."
    except Exception:
        return ''


# ══════════════════════════════════════
# CAPTION WRITERS
# ══════════════════════════════════════

def write_pace_caption(story):
    name      = story['entity_name']
    stat      = story['stat_label']
    stat_col  = story.get('stat', '')
    current   = story['value']
    projected = story['projected']
    games     = story['games_played']
    record    = story['record']
    pid       = story.get('entity_id', '')
    ctx       = story.get('record_context', f'The single-season record is {record}.')

    hook = story['label'] + '.'
    body = f"{current} {stat} through {games} games. {ctx}"

    hist_note   = _historical_note(stat_col, projected)
    career_note = _career_line_batting(pid, stat_col, projected, stat)

    extra_parts = [p for p in [hist_note, career_note] if p]
    extra = ' '.join(extra_parts)

    cta      = "Is this the real deal? 👇"
    hashtags = f"#MLB #Baseball #{name.replace(' ', '')} #FullCountID"

    parts = [hook, body]
    if extra:
        parts.append(extra)
    parts += [cta, hashtags]
    return '\n\n'.join(parts)


def write_streak_caption(story):
    name  = story['entity_name']
    value = story['value']
    kind  = 'hitting' if story['type'] == 'hitting_streak' else 'on-base'
    lede  = story.get('lede', '')

    hook = story['label'] + '.'

    if kind == 'hitting' and value >= 30:
        hist = "A 30-game hitting streak is one of the rarest feats in baseball — DiMaggio's 56-game record from 1941 has never been approached."
    elif kind == 'hitting' and value >= 20:
        hist = "A 20-game hitting streak is elite company — fewer than a handful of players reach it each season."
    elif kind == 'on-base' and value >= 50:
        hist = "Reaching base in 50 consecutive games is historically extraordinary — fewer than 10 players have done it in the modern era."
    else:
        hist = ''

    cta      = "How far does it go? 👇"
    hashtags = f"#MLB #Baseball #{name.replace(' ', '')} #FullCountID"

    parts = [hook]
    if lede:
        parts.append(lede)
    if hist:
        parts.append(hist)
    parts += [cta, hashtags]
    return '\n\n'.join(parts)


def write_outlier_caption(story):
    name     = story['entity_name']
    stat_col = story.get('stat', '')
    value    = story.get('value')
    lede     = story.get('lede', '')
    pid      = story.get('entity_id', '')

    hook = story['label'] + '.'

    hist_note = _historical_note(stat_col, value) if value else ''

    if stat_col == 'era':
        career_note = _career_line_pitching(pid, 'era', value, 'ERA')
    else:
        label_map = {'ops': 'OPS', 'avg': 'AVG'}
        career_note = _career_line_batting(pid, stat_col, value, label_map.get(stat_col, stat_col.upper()))

    extra_parts = [p for p in [hist_note, career_note] if p]
    extra = ' '.join(extra_parts)

    cta      = "The numbers don't lie. 👇"
    hashtags = f"#MLB #Baseball #Statcast #{name.replace(' ', '')} #FullCountID"

    parts = [hook]
    if lede:
        parts.append(lede)
    if extra:
        parts.append(extra)
    parts += [cta, hashtags]
    return '\n\n'.join(parts)


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
