import datetime
from data.database import get_connection

# ══════════════════════════════════════
# FAME TIERS
# ══════════════════════════════════════

FAME_TIER = {
    # Tier 1 — global superstars (1.5x)
    'Shohei Ohtani': 1.5, 'Aaron Judge': 1.5, 'Mookie Betts': 1.5,
    'Mike Trout': 1.5,

    # Tier 2 — marquee stars (1.4x)
    'Freddie Freeman': 1.4, 'Yordan Alvarez': 1.4,
    'Ronald Acuña Jr.': 1.4, 'Juan Soto': 1.4, 'Fernando Tatis Jr.': 1.4,
    'Bryce Harper': 1.4, 'Paul Skenes': 1.4,

    # Tier 3 — rising stars and fan favorites (1.3x)
    'Julio Rodriguez': 1.3, 'Bobby Witt Jr.': 1.3, 'Gunnar Henderson': 1.3,
    'Elly De La Cruz': 1.3, 'Corbin Carroll': 1.3, 'Jackson Chourio': 1.3,
    'Spencer Strider': 1.3, 'Trea Turner': 1.3,

    # Tier 4 — well known (1.2x)
    'Vladimir Guerrero Jr.': 1.2, 'Bo Bichette': 1.2, 'Pete Alonso': 1.2,
    'Gerrit Cole': 1.2, 'Zack Wheeler': 1.2, 'Max Scherzer': 1.2,
    'Clayton Kershaw': 1.2, 'Jacob deGrom': 1.2, 'Ben Rice': 1.2,
    'Nick Kurtz': 1.2, 'Cody Bellinger': 1.2, 'Jose Ramirez': 1.2,
    'Freddy Peralta': 1.2, 'Tarik Skubal': 1.2,

    # Tier 5 — solid following (1.1x)
    'Ildemaro Vargas': 1.0,  # utility player — no bump despite hot start
}

def get_fame_multiplier(player_name):
    return FAME_TIER.get(player_name, 1.0)

# ══════════════════════════════════════
# RECENCY CHECK
# ══════════════════════════════════════

def days_since_last_post(entity_id, story_type):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT posted_date FROM story_log
        WHERE entity_id = ? AND story_type = ? AND posted = 1
        ORDER BY posted_date DESC LIMIT 1
    ''', (entity_id, story_type))
    row = c.fetchone()
    conn.close()
    if not row or not row['posted_date']:
        return 999
    last = datetime.datetime.strptime(row['posted_date'], '%Y-%m-%d').date()
    return (datetime.date.today() - last).days


def days_since_last_type_post(story_type):
    """Days since ANY story of this type was posted (any player)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT posted_date FROM story_log
        WHERE story_type = ? AND posted = 1
        ORDER BY posted_date DESC LIMIT 1
    ''', (story_type,))
    row = c.fetchone()
    conn.close()
    if not row or not row['posted_date']:
        return 999
    last = datetime.datetime.strptime(row['posted_date'], '%Y-%m-%d').date()
    return (datetime.date.today() - last).days

COOLDOWN_DAYS = {
    'hitting_streak': 5,
    'onbase_streak':  5,
    'pace':           7,
    'outlier_ops':    14,
    'outlier_avg':    14,
    'outlier_era':    14,
    'cold_streak':    7,
    'era_spike':      7,
}

# ══════════════════════════════════════
# MINIMUM GAMES THRESHOLDS
# Story types that require a minimum number
# of games before they're eligible to post
# ══════════════════════════════════════

MIN_GAMES = {
    'pace':           30,
    'outlier_ops':    25,
    'outlier_avg':    25,
    'outlier_era':    15,
    'hitting_streak': 0,
    'onbase_streak':  0,
    'cold_streak':    15,
    'era_spike':      8,
}

# ══════════════════════════════════════
# SCORER
# ══════════════════════════════════════

def score_candidate(candidate):
    story_type  = candidate['type']
    rarity      = candidate.get('raw_rarity', 0.5)
    name        = candidate.get('entity_name', '')
    entity_id   = candidate.get('entity_id', '')
    games_played = candidate.get('games_played', 999)

    # Minimum games check — suppress early season noise
    min_g = MIN_GAMES.get(story_type, 0)
    if games_played < min_g:
        return None

    rarity_score = min(rarity, 1.0)

    # Recency — suppress if posted recently
    days_since = days_since_last_post(entity_id, story_type)
    cooldown   = COOLDOWN_DAYS.get(story_type, 7)
    if days_since < cooldown:
        return None

    recency_score = 1.0 if days_since >= 999 else min(days_since / cooldown, 1.0)

    fame   = get_fame_multiplier(name)
    visual = {
        'hitting_streak': 0.9, 'onbase_streak': 0.9,
        'pace':           1.0,
        'outlier_ops':    0.8, 'outlier_avg': 0.8, 'outlier_era': 0.8,
        'cold_streak':    0.85, 'era_spike': 0.85,
    }.get(story_type, 0.8)

    # Global type penalty — if this story type was posted recently by anyone,
    # push it down so different types surface instead
    type_days     = days_since_last_type_post(story_type)
    type_cooldown = COOLDOWN_DAYS.get(story_type, 7)
    type_penalty  = 1.0 if type_days >= type_cooldown else 0.65

    novelty      = (rarity_score * 0.7) + (recency_score * 0.3)
    shareability = (min(fame / 1.5, 1.0) * 0.6) + (visual * 0.4)
    final_score  = round(((novelty * 0.6) + (shareability * 0.4)) * 100 * type_penalty, 1)

    return {
        **candidate,
        'rarity_score':  round(rarity_score, 3),
        'recency_score': round(recency_score, 3),
        'fame':          fame,
        'visual_score':  visual,
        'novelty':       round(novelty, 3),
        'shareability':  round(shareability, 3),
        'final_score':   final_score,
    }

# ══════════════════════════════════════
# RANK AND SELECT TOP N
# ══════════════════════════════════════

def rank_candidates(candidates, top_n=5):
    scored   = []
    for c in candidates:
        result = score_candidate(c)
        if result is not None:
            scored.append(result)

    scored.sort(key=lambda x: x['final_score'], reverse=True)

    seen_players   = {}  # entity_id → count (max 1 per player)
    seen_types     = {}  # story_type → count (max 2 per type)
    seen_type_stat = {}  # (story_type, stat) → count (max 1 per type+stat combo)
    filtered = []

    for s in scored:
        pid       = s['entity_id']
        stype     = s['type']
        stat      = s.get('stat', '')
        type_stat = (stype, stat)

        if seen_players.get(pid, 0) >= 1:
            continue
        if seen_types.get(stype, 0) >= 2:
            continue
        if seen_type_stat.get(type_stat, 0) >= 1:
            continue

        filtered.append(s)
        seen_players[pid]         = seen_players.get(pid, 0) + 1
        seen_types[stype]         = seen_types.get(stype, 0) + 1
        seen_type_stat[type_stat] = seen_type_stat.get(type_stat, 0) + 1

    # If strict filtering left fewer than top_n, do a relaxed pass
    # (different players only, still respect type cap and type+stat cap)
    if len(filtered) < top_n:
        used_ids       = {s['entity_id'] for s in filtered}
        seen_types2    = dict(seen_types)
        seen_type_stat2 = dict(seen_type_stat)
        for s in scored:
            if len(filtered) >= top_n:
                break
            if s['entity_id'] in used_ids:
                continue
            stype     = s['type']
            type_stat = (stype, s.get('stat', ''))
            if seen_types2.get(stype, 0) >= 2:
                continue
            if seen_type_stat2.get(type_stat, 0) >= 1:
                continue
            filtered.append(s)
            used_ids.add(s['entity_id'])
            seen_types2[stype]        = seen_types2.get(stype, 0) + 1
            seen_type_stat2[type_stat] = seen_type_stat2.get(type_stat, 0) + 1

    return filtered[:top_n]

if __name__ == '__main__':
    from engine.detectors import run_all_detectors
    candidates = run_all_detectors()
    top = rank_candidates(candidates)
    print("\n=== TODAY'S TOP STORIES ===\n")
    for i, s in enumerate(top, 1):
        print(f"{i}. [{s['final_score']}] {s['entity_name']} — {s['label']}")
        print(f"   Rarity: {s['rarity_score']} | Fame: {s['fame']} | Games: {s.get('games_played', 'N/A')} | Type: {s['type']}")
        print()
