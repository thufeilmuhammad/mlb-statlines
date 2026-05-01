import datetime
from data.database import get_connection

def get_current_season():
    return datetime.date.today().year

def get_today():
    return datetime.date.today().strftime('%Y-%m-%d')

# ══════════════════════════════════════
# STREAK DETECTOR
# Finds active hitting and on-base streaks
# ══════════════════════════════════════

def detect_streaks(min_hitting=10, min_onbase=10):
    conn = get_connection()
    c = conn.cursor()
    candidates = []

    # Get all players who have game logs
    c.execute('SELECT DISTINCT player_id, player_name, team FROM game_logs')
    players = c.fetchall()

    for player in players:
        pid = player['player_id']
        name = player['player_name']
        team = player['team']

        # Get all game logs for this player sorted most recent first
        c.execute('''
            SELECT game_date, hits, reached_base, obp
            FROM game_logs
            WHERE player_id = ?
            ORDER BY game_date DESC
        ''', (pid,))
        logs = c.fetchall()

        if not logs:
            continue

        # Count hitting streak
        hitting_streak = 0
        for log in logs:
            if log['hits'] and log['hits'] > 0:
                hitting_streak += 1
            else:
                break

        # Count on-base streak
        onbase_streak = 0
        for log in logs:
            if log['reached_base'] and log['reached_base'] == 1:
                onbase_streak += 1
            else:
                break

        # Only emit at milestone crossings
        milestones = [10, 15, 20, 25, 30, 35, 40]

        if hitting_streak in milestones:
            candidates.append({
                'type': 'hitting_streak',
                'entity_id': pid,
                'entity_name': name,
                'team': team,
                'value': hitting_streak,
                'stat': 'hits',
                'label': f'{hitting_streak}-game hitting streak',
                'raw_rarity': hitting_streak / 56,  # 56 is all-time record
            })

        if onbase_streak in milestones:
            candidates.append({
                'type': 'onbase_streak',
                'entity_id': pid,
                'entity_name': name,
                'team': team,
                'value': onbase_streak,
                'stat': 'reached_base',
                'label': f'{onbase_streak}-game on-base streak',
                'raw_rarity': onbase_streak / 84,  # 84 is all-time record
            })

    conn.close()
    print(f"Streak detector found {len(candidates)} candidates.")
    return candidates


# ══════════════════════════════════════
# PACE DETECTOR
# Finds players on historic season paces
# ══════════════════════════════════════

PACE_TARGETS = {
    'hr':  {'label': 'home runs', 'records': {'season': 73, 'notable': [50, 60, 62, 73]}},
    'rbi': {'label': 'RBI',       'records': {'season': 191, 'notable': [120, 140, 160]}},
    'hits':{'label': 'hits',      'records': {'season': 262, 'notable': [200, 220, 240]}},
    'sb':  {'label': 'stolen bases', 'records': {'season': 130, 'notable': [60, 80, 100]}},
}

def detect_pace(min_games=20):
    conn = get_connection()
    c = conn.cursor()
    candidates = []
    season = get_current_season()

    c.execute('''
        SELECT player_id, player_name, team, g, hr, rbi, hits, sb, avg, ops
        FROM season_batting
        WHERE season = ? AND g >= ?
    ''', (season, min_games))
    players = c.fetchall()

    total_games = 162

    for player in players:
        pid = player['player_id']
        name = player['player_name']
        team = player['team']
        games = player['g']

        for stat, meta in PACE_TARGETS.items():
            current = player[stat] if player[stat] else 0
            if current == 0:
                continue

            projected = round(current / games * total_games)
            record = meta['records']['season']

            # Only interesting if projected is notable
            is_notable = False
            for threshold in meta['records']['notable']:
                if projected >= threshold:
                    is_notable = True
                    break

            if not is_notable:
                continue

            rarity = min(projected / record, 1.0)

            candidates.append({
                'type': 'pace',
                'entity_id': pid,
                'entity_name': name,
                'team': team,
                'value': current,
                'projected': projected,
                'stat': stat,
                'stat_label': meta['label'],
                'games_played': games,
                'record': record,
                'label': f'On pace for {projected} {meta["label"]}',
                'raw_rarity': rarity,
            })

    conn.close()
    print(f"Pace detector found {len(candidates)} candidates.")
    return candidates


# ══════════════════════════════════════
# OUTLIER DETECTOR
# Finds players with extreme season stats
# ══════════════════════════════════════

def detect_outliers(min_games=20):
    conn = get_connection()
    c = conn.cursor()
    candidates = []
    season = get_current_season()

    # Batting outliers
    c.execute('''
        SELECT player_id, player_name, team, g, avg, obp, slg, ops, hr, sb
        FROM season_batting
        WHERE season = ? AND g >= ?
    ''', (season, min_games))
    batters = c.fetchall()

    if batters:
        ops_vals = [b['ops'] for b in batters if b['ops']]
        avg_vals = [b['avg'] for b in batters if b['avg']]

        ops_mean = sum(ops_vals) / len(ops_vals)
        avg_mean = sum(avg_vals) / len(avg_vals)

        ops_std = (sum((x - ops_mean) ** 2 for x in ops_vals) / len(ops_vals)) ** 0.5
        avg_std = (sum((x - avg_mean) ** 2 for x in avg_vals) / len(avg_vals)) ** 0.5

        for b in batters:
            pid = b['player_id']
            name = b['player_name']
            team = b['team']

            # OPS outlier
            if ops_std > 0 and b['ops']:
                ops_z = (b['ops'] - ops_mean) / ops_std
                if ops_z >= 2.5:
                    candidates.append({
                        'type': 'outlier_ops',
                        'entity_id': pid,
                        'entity_name': name,
                        'team': team,
                        'value': b['ops'],
                        'z_score': round(ops_z, 2),
                        'stat': 'ops',
                        'label': f'{name} OPS {b["ops"]} — {round(ops_z, 1)} std devs above average',
                        'raw_rarity': min(ops_z / 4, 1.0),
                    })

            # AVG outlier
            if avg_std > 0 and b['avg']:
                avg_z = (b['avg'] - avg_mean) / avg_std
                if avg_z >= 2.5:
                    candidates.append({
                        'type': 'outlier_avg',
                        'entity_id': pid,
                        'entity_name': name,
                        'team': team,
                        'value': b['avg'],
                        'z_score': round(avg_z, 2),
                        'stat': 'avg',
                        'label': f'{name} batting {b["avg"]} — {round(avg_z, 1)} std devs above average',
                        'raw_rarity': min(avg_z / 4, 1.0),
                    })

    # Pitching outliers — ERA
    c.execute('''
        SELECT player_id, player_name, team, g, gs, ip, era, k, whip, k9
        FROM season_pitching
        WHERE season = ? AND g >= ?
    ''', (season, min_games))
    pitchers = c.fetchall()

    if pitchers:
        era_vals = [p['era'] for p in pitchers if p['era'] and p['era'] > 0]
        if era_vals:
            era_mean = sum(era_vals) / len(era_vals)
            era_std = (sum((x - era_mean) ** 2 for x in era_vals) / len(era_vals)) ** 0.5

            for p in pitchers:
                if not p['era'] or p['era'] == 0:
                    continue
                if era_std > 0:
                    # For ERA lower is better so flip the z-score
                    era_z = (era_mean - p['era']) / era_std
                    if era_z >= 2.0:
                        candidates.append({
                            'type': 'outlier_era',
                            'entity_id': p['player_id'],
                            'entity_name': p['player_name'],
                            'team': p['team'],
                            'value': p['era'],
                            'z_score': round(era_z, 2),
                            'stat': 'era',
                            'label': f'{p["player_name"]} ERA {p["era"]} — elite among starters',
                            'raw_rarity': min(era_z / 4, 1.0),
                        })

    conn.close()
    print(f"Outlier detector found {len(candidates)} candidates.")
    return candidates


# ══════════════════════════════════════
# RUN ALL DETECTORS
# ══════════════════════════════════════

def run_all_detectors():
    print("\n=== Running story detectors ===\n")
    candidates = []
    candidates += detect_streaks()
    candidates += detect_pace()
    candidates += detect_outliers()
    print(f"\nTotal candidates found: {len(candidates)}")
    return candidates

if __name__ == '__main__':
    results = run_all_detectors()
    print("\n=== TOP CANDIDATES ===")
    for c in results[:10]:
        print(f"[{c['type']}] {c['entity_name']} — {c['label']} (rarity: {c['raw_rarity']:.2f})")