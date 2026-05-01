import datetime
from data.database import get_connection

# ══════════════════════════════════════
# FAME TIERS
# Multiplier applied to shareability score
# ══════════════════════════════════════

FAME_TIER = {
    # Tier 1 — global superstars (1.5x)
    'Shohei Ohtani': 1.5, 'Aaron Judge': 1.5, 'Mookie Betts': 1.5,
    'Freddie Freeman': 1.4, 'Yordan Alvarez': 1.4, 'Mike Trout': 1.5,
    'Ronald Acuña Jr.': 1.4, 'Juan Soto': 1.4, 'Fernando Tatis Jr.': 1.4,
    'Bryce Harper': 1.4, 'Trea Turner': 1.3, 'Julio Rodriguez': 1.3,
    'Bobby Witt Jr.': 1.3, 'Gunnar Henderson': 1.3, 'Elly De La Cruz': 1.3,
    'Paul Skenes': 1.4, 'Corbin Carroll': 1.3, 'Jackson Chourio': 1.3,
    'Vladimir Guerrero Jr.': 1.3, 'Bo Bichette': 1.2, 'Pete Alonso': 1.2,
    'Gerrit Cole': 1.2, 'Spencer Strider': 1.3, 'Zack Wheeler': 1.2,
    'Max Scherzer': 1.2, 'Clayton Kershaw': 1.2, 'Jacob deGrom': 1.2,
    'Ben Rice': 1.2, 'Cody Bellinger': 1.1,
}

def get_fame_multiplier(player_name):
    return FAME_TIER.get(player_name, 1.0)

# ══════════════════════════════════════
# RECENCY CHECK
# Suppresses stories posted too recently
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
        return 999  # Never posted — no penalty
    last = datetime.datetime.strptime(row['posted_date'], '%Y-%m-%d').date()
    today = datetime.date.today()
    return (today - last).days

COOLDOWN_DAYS = {
    'hitting_streak': 5,
    'onbase_streak': 5,
    'pace': 7,
    'outlier_ops': 14,
    'outlier_avg': 14,
    'outlier_era': 14,
}

# ══════════════════════════════════════
# SCORER
# ══════════════════════════════════════

def score_candidate(candidate):
    story_type = candidate['type']
    rarity = candidate.get('raw_rarity', 0.5)
    name = candidate.get('entity_name', '')
    entity_id = candidate.get('entity_id', '')

    # Rarity score — 0 to 1
    rarity_score = min(rarity, 1.0)

    # Recency penalty — suppress if posted recently
    days_since = days_since_last_post(entity_id, story_type)
    cooldown = COOLDOWN_DAYS.get(story_type, 7)
    if days_since < cooldown:
        return None  # Suppressed

    # Recency bonus — reward fresh stories
    recency_score = 1.0 if days_since >= 999 else min(days_since / cooldown, 1.0)

    # Fame multiplier
    fame = get_fame_multiplier(name)

    # Visual potential — some story types make better graphics
    visual_scores = {
        'hitting_streak': 0.9,
        'onbase_streak': 0.9,
        'pace': 1.0,
        'outlier_ops': 0.8,
        'outlier_avg': 0.8,
        'outlier_era': 0.8,
    }
    visual = visual_scores.get(story_type, 0.8)

    # Final score formula
    # Novelty (rarity + recency) = 60%, Shareability (fame + visual) = 40%
    novelty = (rarity_score * 0.7) + (recency_score * 0.3)
    shareability = (min(fame / 1.5, 1.0) * 0.6) + (visual * 0.4)
    final_score = round(((novelty * 0.6) + (shareability * 0.4)) * 100, 1)

    return {
        **candidate,
        'rarity_score': round(rarity_score, 3),
        'recency_score': round(recency_score, 3),
        'fame': fame,
        'visual_score': visual,
        'novelty': round(novelty, 3),
        'shareability': round(shareability, 3),
        'final_score': final_score,
    }

# ══════════════════════════════════════
# RANK AND SELECT TOP N
# ══════════════════════════════════════

def rank_candidates(candidates, top_n=5):
    scored = []
    for c in candidates:
        result = score_candidate(c)
        if result is not None:
            scored.append(result)

    # Sort by final score descending
    scored.sort(key=lambda x: x['final_score'], reverse=True)

    # Deduplicate — max 2 stories per player
    seen_players = {}
    filtered = []
    for s in scored:
        pid = s['entity_id']
        count = seen_players.get(pid, 0)
        if count < 2:
            filtered.append(s)
            seen_players[pid] = count + 1

    return filtered[:top_n]

if __name__ == '__main__':
    from engine.detectors import run_all_detectors
    candidates = run_all_detectors()
    top = rank_candidates(candidates)
    print("\n=== TODAY'S TOP STORIES ===\n")
    for i, s in enumerate(top, 1):
        print(f"{i}. [{s['final_score']}] {s['entity_name']} — {s['label']}")
        print(f"   Rarity: {s['rarity_score']} | Fame: {s['fame']} | Visual: {s['visual_score']}")
        print()