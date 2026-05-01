import requests
import datetime
import time
from pybaseball import statcast
from data.database import get_connection
from pybaseball import batting_stats, pitching_stats
import warnings
warnings.filterwarnings('ignore')

TEAM_NAME_TO_ABBR = {
    'New York Yankees': 'NYY', 'Boston Red Sox': 'BOS', 'Baltimore Orioles': 'BAL',
    'Tampa Bay Rays': 'TBR', 'Toronto Blue Jays': 'TOR', 'Houston Astros': 'HOU',
    'Los Angeles Angels': 'LAA', 'Seattle Mariners': 'SEA', 'Oakland Athletics': 'OAK',
    'Texas Rangers': 'TEX', 'Athletics': 'ATH', 'Cleveland Guardians': 'CLE',
    'Chicago White Sox': 'CWS', 'Detroit Tigers': 'DET', 'Kansas City Royals': 'KCR',
    'Minnesota Twins': 'MIN', 'New York Mets': 'NYM', 'Atlanta Braves': 'ATL',
    'Miami Marlins': 'MIA', 'Philadelphia Phillies': 'PHI', 'Washington Nationals': 'WSN',
    'Chicago Cubs': 'CHC', 'Cincinnati Reds': 'CIN', 'Milwaukee Brewers': 'MIL',
    'Pittsburgh Pirates': 'PIT', 'St. Louis Cardinals': 'STL', 'Arizona Diamondbacks': 'ARI',
    'Colorado Rockies': 'COL', 'Los Angeles Dodgers': 'LAD', 'San Diego Padres': 'SDP',
    'San Francisco Giants': 'SFG',
}

MLB_API = "https://statsapi.mlb.com/api/v1"

def get_yesterday():
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    return yesterday.strftime('%Y-%m-%d')

def get_today():
    return datetime.date.today().strftime('%Y-%m-%d')

def get_current_season():
    return datetime.date.today().year

# ── FETCH GAMES FROM YESTERDAY ──
def fetch_game_pks(date):
    url = f"{MLB_API}/schedule?sportId=1&date={date}"
    r = requests.get(url, timeout=10)
    data = r.json()
    pks = []
    if 'dates' not in data or not data['dates']:
        print(f"No games found for {date}")
        return pks
    for game in data['dates'][0]['games']:
        pks.append(game['gamePk'])
    print(f"Found {len(pks)} games on {date}")
    return pks

# ── FETCH BOX SCORE FOR ONE GAME ──
def fetch_box_score(game_pk, game_date):
    url = f"{MLB_API}/game/{game_pk}/boxscore"
    r = requests.get(url, timeout=10)
    data = r.json()
    conn = get_connection()
    c = conn.cursor()

    for side in ['home', 'away']:
        team = data['teams'][side]['team']['abbreviation']
        batters = data['teams'][side].get('batters', [])
        pitchers = data['teams'][side].get('pitchers', [])
        players = data['teams'][side]['players']

        # Batters
        for pid in batters:
            key = f"ID{pid}"
            if key not in players:
                continue
            p = players[key]
            name = p['person']['fullName']
            stats = p.get('stats', {}).get('batting', {})
            if not stats:
                continue

            ab   = stats.get('atBats', 0)
            hits = stats.get('hits', 0)
            bb   = stats.get('baseOnBalls', 0)
            hbp  = stats.get('hitByPitch', 0)
            sf   = stats.get('sacFlies', 0)
            pa   = stats.get('plateAppearances', 0)
            hr   = stats.get('homeRuns', 0)
            reached = 1 if (hits + bb + hbp) > 0 else 0

            obp = (hits + bb + hbp) / (ab + bb + hbp + sf) if (ab + bb + hbp + sf) > 0 else 0
            avg = hits / ab if ab > 0 else 0
            doubles = stats.get('doubles', 0)
            triples = stats.get('triples', 0)
            tb = hits + doubles + (2 * triples) + (3 * hr)
            slg = tb / ab if ab > 0 else 0
            ops = obp + slg

            try:
                c.execute('''
                    INSERT OR IGNORE INTO game_logs
                    (player_id, player_name, team, game_date, game_pk,
                     pa, ab, hits, doubles, triples, hr, rbi, bb, k,
                     hbp, reached_base, obp, avg, slg, ops)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    str(pid), name, team, game_date, str(game_pk),
                    pa, ab, hits, doubles, triples, hr,
                    stats.get('rbi', 0), bb, stats.get('strikeOuts', 0),
                    hbp, reached, round(obp, 3), round(avg, 3),
                    round(slg, 3), round(ops, 3)
                ))
            except Exception as e:
                print(f"Error inserting batter {name}: {e}")

        # Pitchers
        for pid in pitchers:
            key = f"ID{pid}"
            if key not in players:
                continue
            p = players[key]
            name = p['person']['fullName']
            stats = p.get('stats', {}).get('pitching', {})
            if not stats:
                continue

            ip_str = str(stats.get('inningsPitched', '0.0'))
            try:
                ip = float(ip_str)
            except:
                ip = 0.0

            er = stats.get('earnedRuns', 0)
            era = round((er / ip * 9), 2) if ip > 0 else 0.0
            hits_a = stats.get('hits', 0)
            bb_p = stats.get('baseOnBalls', 0)
            whip = round((hits_a + bb_p) / ip, 2) if ip > 0 else 0.0

            try:
                c.execute('''
                    INSERT OR IGNORE INTO pitcher_logs
                    (player_id, player_name, team, game_date, game_pk,
                     ip, hits_allowed, runs, er, bb, k, hr_allowed,
                     pitch_count, era, whip)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    str(pid), name, team, game_date, str(game_pk),
                    ip, hits_a,
                    stats.get('runs', 0), er, bb_p,
                    stats.get('strikeOuts', 0),
                    stats.get('homeRuns', 0),
                    stats.get('numberOfPitches', 0),
                    era, whip
                ))
            except Exception as e:
                print(f"Error inserting pitcher {name}: {e}")

    conn.commit()
    conn.close()

# ── FETCH SEASON STATS VIA PYBASEBALL ──
def fetch_season_batting():
    season = get_current_season()
    print(f"Fetching {season} season batting stats...")
    try:
        url = f"{MLB_API}/stats?stats=season&group=hitting&gameType=R&season={season}&limit=500&offset=0&sportId=1"
        r = requests.get(url, timeout=10)
        data = r.json()
        conn = get_connection()
        c = conn.cursor()
        today = get_today()
        for p in data.get('stats', [{}])[0].get('splits', []):
            s = p.get('stat', {})
            player = p.get('player', {})
            team_full = p.get('team', {}).get('name', '')
            team = TEAM_NAME_TO_ABBR.get(team_full, team_full)
            ab = int(s.get('atBats', 0))
            hits = int(s.get('hits', 0))
            bb = int(s.get('baseOnBalls', 0))
            hbp = int(s.get('hitByPitch', 0))
            sf = int(s.get('sacFlies', 0))
            hr = int(s.get('homeRuns', 0))
            doubles = int(s.get('doubles', 0))
            triples = int(s.get('triples', 0))
            tb = hits + doubles + (2 * triples) + (3 * hr)
            pa = ab + bb + hbp + sf
            avg = round(hits / ab, 3) if ab > 0 else 0
            obp = round((hits + bb + hbp) / (ab + bb + hbp + sf), 3) if (ab + bb + hbp + sf) > 0 else 0
            slg = round(tb / ab, 3) if ab > 0 else 0
            ops = round(obp + slg, 3)
            try:
                c.execute('''
                    INSERT OR REPLACE INTO season_batting
                    (player_id, player_name, team, season, g, pa, ab,
                     hits, hr, rbi, sb, avg, obp, slg, ops, woba, war, pulled_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    str(player.get('id', '')),
                    player.get('fullName', ''),
                    team, season,
                    int(s.get('gamesPlayed', 0)),
                    pa, ab, hits, hr,
                    int(s.get('rbi', 0)),
                    int(s.get('stolenBases', 0)),
                    avg, obp, slg, ops,
                    0.0, 0.0,
                    today
                ))
            except Exception as e:
                print(f"Error inserting batting row: {e}")
        conn.commit()
        conn.close()
        print(f"Batting stats saved — {len(data.get('stats', [{}])[0].get('splits', []))} players.")
    except Exception as e:
        print(f"Failed to fetch batting stats: {e}")

def fetch_season_pitching():
    season = get_current_season()
    print(f"Fetching {season} season pitching stats...")
    try:
        url = f"{MLB_API}/stats?stats=season&group=pitching&gameType=R&season={season}&limit=500&offset=0&sportId=1"
        r = requests.get(url, timeout=10)
        data = r.json()
        conn = get_connection()
        c = conn.cursor()
        today = get_today()
        for p in data.get('stats', [{}])[0].get('splits', []):
            s = p.get('stat', {})
            player = p.get('player', {})
            team_full = p.get('team', {}).get('name', '')
            team = TEAM_NAME_TO_ABBR.get(team_full, team_full)
            ip_str = str(s.get('inningsPitched', '0.0'))
            try:
                ip = float(ip_str)
            except:
                ip = 0.0
            er = int(s.get('earnedRuns', 0))
            hits_a = int(s.get('hits', 0))
            bb = int(s.get('baseOnBalls', 0))
            era = round(er / ip * 9, 2) if ip > 0 else 0.0
            whip = round((hits_a + bb) / ip, 2) if ip > 0 else 0.0
            k = int(s.get('strikeOuts', 0))
            k9 = round(k / ip * 9, 2) if ip > 0 else 0.0
            bb9 = round(bb / ip * 9, 2) if ip > 0 else 0.0
            try:
                c.execute('''
                    INSERT OR REPLACE INTO season_pitching
                    (player_id, player_name, team, season, g, gs, ip,
                     w, l, sv, k, bb, hr, era, whip, k9, bb9, fip, war, pulled_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    str(player.get('id', '')),
                    player.get('fullName', ''),
                    team, season,
                    int(s.get('gamesPlayed', 0)),
                    int(s.get('gamesStarted', 0)),
                    ip,
                    int(s.get('wins', 0)),
                    int(s.get('losses', 0)),
                    int(s.get('saves', 0)),
                    k, bb,
                    int(s.get('homeRuns', 0)),
                    era, whip, k9, bb9,
                    0.0, 0.0,
                    today
                ))
            except Exception as e:
                print(f"Error inserting pitching row: {e}")
        conn.commit()
        conn.close()
        print(f"Pitching stats saved — {len(data.get('stats', [{}])[0].get('splits', []))} pitchers.")
    except Exception as e:
        print(f"Failed to fetch pitching stats: {e}")

# ── FETCH STANDINGS ──
def fetch_standings():
    season = get_current_season()
    print("Fetching standings...")
    url = f"{MLB_API}/standings?leagueId=103,104&season={season}&standingsTypes=regularSeason"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        conn = get_connection()
        c = conn.cursor()
        today = get_today()
        division_map = {
            200: 'AL West', 201: 'AL East', 202: 'AL Central',
            203: 'NL West', 204: 'NL East', 205: 'NL Central'
        }
        for record in data.get('records', []):
            div_id = record['division']['id']
            division = division_map.get(div_id, 'Unknown')
            for tr in record['teamRecords']:
                team = tr['team']['name']
                w = tr['wins']
                l = tr['losses']
                pct = tr['winningPercentage']
                gb = tr.get('gamesBack', '-')
                try:
                    c.execute('''
                        INSERT OR IGNORE INTO standings
                        (team, division, w, l, pct, gb, pulled_date)
                        VALUES (?,?,?,?,?,?,?)
                    ''', (team, division, w, l, pct, gb, today))
                except Exception as e:
                    print(f"Error inserting standings: {e}")
        conn.commit()
        conn.close()
        print("Standings saved.")
    except Exception as e:
        print(f"Failed to fetch standings: {e}")

# ── MASTER DAILY PULL ──
def run_daily_pull():
    date = get_yesterday()
    print(f"\n=== Full Count — Daily Pull for {date} ===\n")

    # Box scores
    pks = fetch_game_pks(date)
    for pk in pks:
        print(f"Fetching box score: game {pk}")
        fetch_box_score(pk, date)
        time.sleep(0.5)

    # Season stats
    fetch_season_batting()
    fetch_season_pitching()

    # Standings
    fetch_standings()

    print("\n=== Pull complete ===\n")

if __name__ == '__main__':
    run_daily_pull()