import datetime
from data.database import get_connection

def get_current_season():
    return datetime.date.today().year

def get_today():
    return datetime.date.today().strftime('%Y-%m-%d')

# ══════════════════════════════════════
# STREAK DETECTOR
# ══════════════════════════════════════

def detect_streaks(min_hitting=10, min_onbase=10):
    conn = get_connection()
    c = conn.cursor()
    candidates = []

    c.execute('SELECT DISTINCT player_id, player_name, team FROM game_logs')
    players = c.fetchall()

    for player in players:
        pid  = player['player_id']
        name = player['player_name']
        team = player['team']

        c.execute('''
            SELECT game_date, hits, reached_base, obp
            FROM game_logs WHERE player_id = ?
            ORDER BY game_date DESC
        ''', (pid,))
        logs = c.fetchall()
        if not logs:
            continue

        hitting_streak = 0
        for log in logs:
            if log['hits'] and log['hits'] > 0: hitting_streak += 1
            else: break

        onbase_streak = 0
        for log in logs:
            if log['reached_base'] and log['reached_base'] == 1: onbase_streak += 1
            else: break

        milestones = [10, 15, 20, 25, 30, 35, 40]

        if hitting_streak in milestones:
            candidates.append({
                'type': 'hitting_streak',
                'entity_id': pid, 'entity_name': name, 'team': team,
                'value': hitting_streak, 'stat': 'hits',
                'label': f'{name} has hit safely in {hitting_streak} straight games',
                'headline': f'{name} has hit safely in {hitting_streak} consecutive games',
                'lede': f'The {team} star has recorded at least one hit in each of the last {hitting_streak} games — one of the longest active hitting streaks in baseball.',
                'context': f'{name} has hit safely in {hitting_streak} consecutive games. The all-time MLB hitting streak record is 56 games, set by Joe DiMaggio in 1941. Active streaks this long are exceptionally rare in the modern game.',
                'raw_rarity': hitting_streak / 56,
            })

        if onbase_streak in milestones:
            candidates.append({
                'type': 'onbase_streak',
                'entity_id': pid, 'entity_name': name, 'team': team,
                'value': onbase_streak, 'stat': 'reached_base',
                'label': f'{name} has reached base in {onbase_streak} straight games',
                'headline': f'{name} has reached base in {onbase_streak} consecutive games',
                'lede': f'{name} has found a way on base in each of the last {onbase_streak} games — via hit, walk, or hit by pitch.',
                'context': f'{name} has reached base safely in {onbase_streak} consecutive games. On-base streaks at this length speak to elite plate discipline and bat control. Very few players sustain this kind of consistency over a full month.',
                'raw_rarity': onbase_streak / 84,
            })

    conn.close()
    print(f"Streak detector found {len(candidates)} candidates.")
    return candidates


# ══════════════════════════════════════
# PACE DETECTOR
# ══════════════════════════════════════

PACE_TARGETS = {
    'hr': {
        'label': 'home runs',
        'records': {'season': 73, 'notable': [50, 60, 62, 73]},
        'record_holder': 'Barry Bonds',
        'record_year': 2001,
        'record_context': 'Barry Bonds set the all-time single-season record with 73 home runs in 2001. No one has hit 62 or more since. Reaching that territory would be one of the most remarkable power seasons in baseball history.',
    },
    'rbi': {
        'label': 'RBI',
        'records': {'season': 191, 'notable': [120, 140, 160]},
        'record_holder': 'Hack Wilson',
        'record_year': 1930,
        'record_context': 'Hack Wilson drove in 191 runs in 1930 — a record that has stood for nearly a century. No player has topped 165 RBI since. A 140+ RBI season in the modern era would be historically elite.',
    },
    'hits': {
        'label': 'hits',
        'records': {'season': 262, 'notable': [200, 220, 240]},
        'record_holder': 'Ichiro Suzuki',
        'record_year': 2004,
        'record_context': 'Ichiro Suzuki set the modern single-season hits record with 262 in 2004. Reaching 240 hits in a season has only happened a handful of times in baseball history. A pace like this would put this player in elite historical company.',
    },
    'sb': {
        'label': 'stolen bases',
        'records': {'season': 130, 'notable': [60, 80, 100]},
        'record_holder': 'Rickey Henderson',
        'record_year': 1982,
        'record_context': 'Rickey Henderson stole 130 bases in 1982 — a record that may never be broken. Reaching 80 stolen bases in a single season would be the best mark in decades and would instantly define a player\'s legacy.',
    },
}

def detect_pace(min_games=20):
    conn = get_connection()
    c = conn.cursor()
    candidates = []
    season = get_current_season()

    c.execute('''
        SELECT player_id, player_name, team, g, hr, rbi, hits, sb, avg, ops
        FROM season_batting WHERE season = ? AND g >= ?
    ''', (season, min_games))
    players = c.fetchall()

    for player in players:
        pid   = player['player_id']
        name  = player['player_name']
        team  = player['team']
        games = player['g']

        for stat, meta in PACE_TARGETS.items():
            current = player[stat] if player[stat] else 0
            if current == 0:
                continue

            projected = round(current / games * 162)
            record    = meta['records']['season']

            is_notable = any(projected >= t for t in meta['records']['notable'])
            if not is_notable:
                continue

            rarity = min(projected / record, 1.0)
            lbl    = meta['label']

            if projected >= record:
                headline = f"{name} is on pace to break the all-time {lbl} record"
            elif projected >= record * 0.9:
                headline = f"{name} is on pace for {projected} {lbl} — chasing one of the greatest seasons ever"
            else:
                headline = f"{name} is on pace for {projected} {lbl} this season"

            lede = (
                f"{name} has {current} {lbl} through {games} games this season. "
                f"At that rate, he projects for {projected} over a full 162-game season. "
                f"The all-time single-season record is {record}, set by {meta['record_holder']} in {meta['record_year']}."
            )

            context = meta['record_context']

            candidates.append({
                'type': 'pace',
                'entity_id': pid, 'entity_name': name, 'team': team,
                'value': current, 'projected': projected,
                'stat': stat, 'stat_label': lbl,
                'games_played': games, 'record': record,
                'record_holder': meta['record_holder'],
                'record_year': meta['record_year'],
                'record_context': meta['record_context'],
                'label': headline,
                'lede': lede,
                'context': context,
                'raw_rarity': rarity,
            })

    conn.close()
    print(f"Pace detector found {len(candidates)} candidates.")
    return candidates


# ══════════════════════════════════════
# OUTLIER DETECTOR
# ══════════════════════════════════════

def detect_outliers(min_games=20, min_ab=80):
    from engine.scorer import get_fame_multiplier
    conn = get_connection()
    c = conn.cursor()
    candidates = []
    season = get_current_season()

    c.execute('''
        SELECT player_id, player_name, team, g, ab, avg, obp, slg, ops, hr, sb
        FROM season_batting WHERE season = ? AND g >= ? AND ab >= ?
    ''', (season, min_games, min_ab))
    batters = c.fetchall()

    if batters:
        ops_vals = [b['ops'] for b in batters if b['ops']]
        avg_vals = [b['avg'] for b in batters if b['avg']]
        ops_mean = sum(ops_vals) / len(ops_vals)
        avg_mean = sum(avg_vals) / len(avg_vals)
        ops_std  = (sum((x-ops_mean)**2 for x in ops_vals) / len(ops_vals))**0.5
        avg_std  = (sum((x-avg_mean)**2 for x in avg_vals) / len(avg_vals))**0.5

        for b in batters:
            pid  = b['player_id']
            name = b['player_name']
            team = b['team']

            fame = get_fame_multiplier(b['player_name'])
            if ops_std > 0 and b['ops']:
                z = (b['ops'] - ops_mean) / ops_std
                if z >= 2.5 and (fame > 1.0 or b['ab'] >= 120):
                    candidates.append({
                        'type': 'outlier_ops',
                        'entity_id': pid, 'entity_name': name, 'team': team,
                        'value': b['ops'], 'z_score': round(z, 2), 'stat': 'ops',
                        'label': f"{name} is posting a {b['ops']} OPS — one of the best marks in baseball",
                        'headline': f"{name} is posting a {b['ops']} OPS — one of the best marks in baseball",
                        'lede': f"{name} has an OPS of {b['ops']} this season, putting him {round(z,1)} standard deviations above the MLB average. That ranks among the elite offensive performers in the game right now.",
                        'context': f"An OPS above 1.000 is considered exceptional in modern baseball. League average typically sits around .720-.740. A mark of {b['ops']} is the kind of number that defines MVP seasons and gets engraved in record books.",
                        'raw_rarity': min(z/4, 1.0),
                    })

            if avg_std > 0 and b['avg']:
                z = (b['avg'] - avg_mean) / avg_std
                if z >= 2.5 and (fame > 1.0 or b['ab'] >= 120):
                    candidates.append({
                        'type': 'outlier_avg',
                        'entity_id': pid, 'entity_name': name, 'team': team,
                        'value': b['avg'], 'z_score': round(z, 2), 'stat': 'avg',
                        'label': f"{name} is batting {b['avg']} — elite in the modern game",
                        'headline': f"{name} is batting {b['avg']} this season",
                        'lede': f"{name} is hitting {b['avg']} this season — {round(z,1)} standard deviations above the MLB average. In an era where batting average has declined leaguewide, that number stands out.",
                        'context': f"MLB batting average has been trending down for two decades. A mark above .330 in today's game is exceptionally rare. {name} is doing something that very few hitters in baseball can claim right now.",
                        'raw_rarity': min(z/4, 1.0),
                    })

    c.execute('''
        SELECT player_id, player_name, team, g, gs, ip, era, k, whip, k9
        FROM season_pitching WHERE season = ? AND g >= ?
    ''', (season, min_games))
    pitchers = c.fetchall()

    if pitchers:
        era_vals = [p['era'] for p in pitchers if p['era'] and p['era'] > 0]
        if era_vals:
            era_mean = sum(era_vals) / len(era_vals)
            era_std  = (sum((x-era_mean)**2 for x in era_vals) / len(era_vals))**0.5
            for p in pitchers:
                if not p['era'] or p['era'] == 0 or era_std == 0:
                    continue
                z = (era_mean - p['era']) / era_std
                if z >= 2.0:
                    candidates.append({
                        'type': 'outlier_era',
                        'entity_id': p['player_id'], 'entity_name': p['player_name'], 'team': p['team'],
                        'value': p['era'], 'z_score': round(z, 2), 'stat': 'era',
                        'label': f"{p['player_name']} has a {p['era']} ERA — elite among all starters",
                        'headline': f"{p['player_name']} has a {p['era']} ERA this season",
                        'lede': f"{p['player_name']} is sporting a {p['era']} ERA through {p['g']} appearances — putting him {round(z,1)} standard deviations better than the MLB average. Numbers like that belong in the Cy Young conversation.",
                        'context': f"A sub-2.00 ERA over a full season is one of the rarest achievements in baseball. League average ERA typically sits around 4.00-4.50. What {p['player_name']} is doing right now is historically dominant.",
                        'raw_rarity': min(z/4, 1.0),
                    })

    conn.close()
    print(f"Outlier detector found {len(candidates)} candidates.")
    return candidates


# ══════════════════════════════════════
# COLD STREAK DETECTOR
# ══════════════════════════════════════

def detect_cold_streaks(window=7, min_ab=15):
    """Detect notable batters in a significant cold stretch."""
    from engine.scorer import get_fame_multiplier
    conn = get_connection()
    c = conn.cursor()
    candidates = []
    season = get_current_season()

    c.execute('SELECT DISTINCT player_id, player_name, team FROM game_logs')
    players = c.fetchall()

    for player in players:
        pid  = player['player_id']
        name = player['player_name']
        team = player['team']

        c.execute('''
            SELECT game_date, ab, hits, k, bb, hr
            FROM game_logs WHERE player_id = ?
            ORDER BY game_date DESC LIMIT ?
        ''', (pid, window))
        recent = c.fetchall()

        if len(recent) < window:
            continue

        total_ab   = sum(r['ab']   or 0 for r in recent)
        total_hits = sum(r['hits'] or 0 for r in recent)
        total_k    = sum(r['k']    or 0 for r in recent)

        if total_ab < min_ab:
            continue

        recent_avg = round(total_hits / total_ab, 3)
        fame       = get_fame_multiplier(name)
        threshold  = 0.200 if fame > 1.0 else 0.170

        if recent_avg > threshold:
            continue

        c.execute('''
            SELECT avg, ops, g FROM season_batting
            WHERE player_id = ? AND season = ?
        ''', (pid, season))
        row = c.fetchone()
        if not row or not row['avg'] or row['avg'] < 0.210:
            continue

        season_avg   = row['avg']
        games_played = row['g']
        drop         = round(season_avg - recent_avg, 3)
        k_rate       = round(total_k / total_ab, 3) if total_ab > 0 else 0
        rarity       = min((threshold - recent_avg) / threshold + fame / 1.5 * 0.3, 1.0)

        candidates.append({
            'type':         'cold_streak',
            'entity_id':    pid,
            'entity_name':  name,
            'team':         team,
            'value':        recent_avg,
            'stat':         'avg',
            'stat_label':   'batting average',
            'window':       window,
            'recent_avg':   recent_avg,
            'recent_hits':  total_hits,
            'recent_ab':    total_ab,
            'recent_k':     total_k,
            'k_rate':       k_rate,
            'season_avg':   season_avg,
            'games_played': games_played,
            'drop':         drop,
            'label':        f"{name} is batting .{int(recent_avg*1000):03d} over his last {window} games",
            'lede':         (
                f"{name} has gone {total_hits}-for-{total_ab} (.{int(recent_avg*1000):03d}) "
                f"over his last {window} games — a sharp drop from his season average of {season_avg}."
            ),
            'context':      (
                f"A {drop:.3f}-point drop from his season average over a {window}-game stretch "
                f"is a significant slump for a player of {name}'s caliber. "
                f"Strikeout rate in this stretch: {int(k_rate*100)}%. "
                f"The question is whether this is mechanical, bad luck, or something deeper."
            ),
            'raw_rarity':   rarity,
        })

    conn.close()
    print(f"Cold streak detector found {len(candidates)} candidates.")
    return candidates


# ══════════════════════════════════════
# ERA SPIKE DETECTOR
# ══════════════════════════════════════

def detect_era_spike(window=5, min_ip=8.0):
    """Detect pitchers whose ERA has spiked sharply over recent outings."""
    from engine.scorer import get_fame_multiplier
    conn = get_connection()
    c = conn.cursor()
    candidates = []
    season = get_current_season()

    c.execute('SELECT DISTINCT player_id, player_name, team FROM pitcher_logs')
    pitchers = c.fetchall()

    for pitcher in pitchers:
        pid  = pitcher['player_id']
        name = pitcher['player_name']
        team = pitcher['team']

        c.execute('''
            SELECT game_date, ip, er, k, bb, hits_allowed
            FROM pitcher_logs WHERE player_id = ?
            ORDER BY game_date DESC LIMIT ?
        ''', (pid, window))
        recent = c.fetchall()

        if len(recent) < window:
            continue

        total_ip = sum(r['ip'] or 0 for r in recent)
        total_er = sum(r['er'] or 0 for r in recent)
        total_k  = sum(r['k']  or 0 for r in recent)
        total_bb = sum(r['bb'] or 0 for r in recent)

        if total_ip < min_ip:
            continue

        recent_era = round(total_er / total_ip * 9, 2) if total_ip > 0 else 0
        if recent_era < 4.50:
            continue

        c.execute('''
            SELECT era, g, ip FROM season_pitching
            WHERE player_id = ? AND season = ?
        ''', (pid, season))
        row = c.fetchone()
        if not row or not row['era']:
            continue

        season_era = row['era']
        fame       = get_fame_multiplier(name)
        era_spike  = round(recent_era - season_era, 2)

        if season_era >= 5.00 and fame <= 1.0:
            continue
        if era_spike < 1.00:
            continue

        k9     = round(total_k / total_ip * 9, 1) if total_ip > 0 else 0
        rarity = min(era_spike / 6 + fame / 1.5 * 0.3, 1.0)

        candidates.append({
            'type':        'era_spike',
            'entity_id':   pid,
            'entity_name': name,
            'team':        team,
            'value':       recent_era,
            'stat':        'era',
            'stat_label':  'ERA',
            'window':      window,
            'recent_era':  recent_era,
            'season_era':  season_era,
            'era_spike':   era_spike,
            'recent_ip':   total_ip,
            'recent_k':    total_k,
            'recent_bb':   total_bb,
            'k9':          k9,
            'games_played': row['g'],
            'label':       f"{name} has a {recent_era} ERA over his last {window} outings",
            'lede':        (
                f"{name} has posted a {recent_era} ERA over his last {window} outings — "
                f"a sharp spike from his season ERA of {season_era}."
            ),
            'context':     (
                f"A +{era_spike} ERA spike over {window} outings is a significant red flag. "
                f"In that stretch: {k9} K/9, {total_bb} walks allowed. "
                f"Whether it's mechanics, fatigue, or regression, the results demand attention."
            ),
            'raw_rarity':  rarity,
        })

    conn.close()
    print(f"ERA spike detector found {len(candidates)} candidates.")
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
    candidates += detect_cold_streaks()
    candidates += detect_era_spike()
    print(f"\nTotal candidates found: {len(candidates)}")
    return candidates

if __name__ == '__main__':
    results = run_all_detectors()
    print("\n=== TOP CANDIDATES ===")
    for c in results[:10]:
        print(f"[{c['type']}] {c['entity_name']} — {c['label']} (rarity: {c['raw_rarity']:.2f})")
