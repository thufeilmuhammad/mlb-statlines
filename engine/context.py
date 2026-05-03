"""
Generates one-line context strings for digest entries.

For each story type, surfaces:
  - Current MLB rank in the relevant stat
  - Career high (best prior single season) where available
"""

import datetime
from data.database import get_connection

CURRENT_SEASON = datetime.date.today().year

# Minimum games to be included in ranking queries
MIN_BAT_G  = 20
MIN_PITCH_G = 12

# Stat column → human label
STAT_LABEL = {
    'hr':   'HR',
    'rbi':  'RBI',
    'hits': 'H',
    'sb':   'SB',
    'ops':  'OPS',
    'avg':  'AVG',
    'era':  'ERA',
}

ORDINAL = {1:'1st', 2:'2nd', 3:'3rd', 4:'4th', 5:'5th',
           6:'6th', 7:'7th', 8:'8th', 9:'9th', 10:'10th'}

def _ord(n):
    return ORDINAL.get(n, f'{n}th')


def _mlb_rank_batting(stat_col, value, higher_is_better=True):
    """Return MLB rank (1-indexed) for a batter in stat_col."""
    conn = get_connection()
    c = conn.cursor()
    if higher_is_better:
        c.execute(f'''
            SELECT COUNT(*) + 1 AS rank FROM season_batting
            WHERE season = ? AND g >= ? AND {stat_col} > ?
        ''', (CURRENT_SEASON, MIN_BAT_G, value))
    else:
        c.execute(f'''
            SELECT COUNT(*) + 1 AS rank FROM season_batting
            WHERE season = ? AND g >= ? AND {stat_col} < ?
        ''', (CURRENT_SEASON, MIN_BAT_G, value))
    row = c.fetchone()
    conn.close()
    return row['rank'] if row else None


def _mlb_rank_pitching(stat_col, value, higher_is_better=False):
    """Return MLB rank (1-indexed) for a pitcher in stat_col."""
    conn = get_connection()
    c = conn.cursor()
    if higher_is_better:
        c.execute(f'''
            SELECT COUNT(*) + 1 AS rank FROM season_pitching
            WHERE season = ? AND g >= ? AND {stat_col} > ?
        ''', (CURRENT_SEASON, MIN_PITCH_G, value))
    else:
        c.execute(f'''
            SELECT COUNT(*) + 1 AS rank FROM season_pitching
            WHERE season = ? AND g >= ? AND {stat_col} < ? AND {stat_col} > 0
        ''', (CURRENT_SEASON, MIN_PITCH_G, value))
    row = c.fetchone()
    conn.close()
    return row['rank'] if row else None


def _career_high_batting(player_id, stat_col, higher_is_better=True):
    """Return (best_value, season) from season_batting excluding current season."""
    conn = get_connection()
    c = conn.cursor()
    order = 'DESC' if higher_is_better else 'ASC'
    c.execute(f'''
        SELECT {stat_col} AS val, season FROM season_batting
        WHERE player_id = ? AND season < ? AND {stat_col} IS NOT NULL
        ORDER BY {stat_col} {order} LIMIT 1
    ''', (player_id, CURRENT_SEASON))
    row = c.fetchone()
    conn.close()
    return (row['val'], row['season']) if row else (None, None)


def _career_high_pitching(player_id, stat_col, higher_is_better=False):
    """Return (best_value, season) from season_pitching excluding current season."""
    conn = get_connection()
    c = conn.cursor()
    order = 'ASC' if not higher_is_better else 'DESC'
    c.execute(f'''
        SELECT {stat_col} AS val, season FROM season_pitching
        WHERE player_id = ? AND season < ? AND {stat_col} IS NOT NULL AND {stat_col} > 0
        ORDER BY {stat_col} {order} LIMIT 1
    ''', (player_id, CURRENT_SEASON))
    row = c.fetchone()
    conn.close()
    return (row['val'], row['season']) if row else (None, None)


def _pace_context(story):
    stat     = story.get('stat', '')
    value    = story.get('value')       # current season cumulative
    projected = story.get('projected')
    pid      = str(story.get('entity_id', ''))

    col_map = {'hr': 'hr', 'rbi': 'rbi', 'hits': 'hits', 'sb': 'sb'}
    col = col_map.get(stat)
    if not col or value is None:
        return ''

    parts = []

    # Current MLB rank by cumulative stat this season
    rank = _mlb_rank_batting(col, value)
    if rank and rank <= 10:
        lbl = STAT_LABEL.get(col, col.upper())
        parts.append(f'{_ord(rank)} in MLB in {lbl}')

    # Career high (projected vs best prior season)
    best_val, best_yr = _career_high_batting(pid, col)
    if projected is not None and best_val is not None:
        lbl = STAT_LABEL.get(col, col.upper())
        if projected > best_val:
            parts.append(f'career best pace (prev high: {best_val} {lbl} in {best_yr})')
        else:
            parts.append(f'career best was {best_val} {lbl} ({best_yr})')

    return ' · '.join(parts)


def _outlier_ops_context(story):
    value = story.get('value')
    pid   = str(story.get('entity_id', ''))
    parts = []

    rank = _mlb_rank_batting('ops', value)
    if rank and rank <= 15:
        parts.append(f'{_ord(rank)} in MLB in OPS')

    best_val, best_yr = _career_high_batting(pid, 'ops')
    if best_val is not None:
        if value and value > best_val:
            parts.append(f'career best (prev high: {best_val} in {best_yr})')
        else:
            parts.append(f'career best was {best_val} ({best_yr})')

    return ' · '.join(parts)


def _outlier_avg_context(story):
    value = story.get('value')
    pid   = str(story.get('entity_id', ''))
    parts = []

    rank = _mlb_rank_batting('avg', value)
    if rank and rank <= 15:
        parts.append(f'{_ord(rank)} in MLB in AVG')

    best_val, best_yr = _career_high_batting(pid, 'avg')
    if best_val is not None:
        if value and value > best_val:
            parts.append(f'career best (prev high: {best_val} in {best_yr})')
        else:
            parts.append(f'career best was {best_val} ({best_yr})')

    return ' · '.join(parts)


def _outlier_era_context(story):
    value = story.get('value')
    pid   = str(story.get('entity_id', ''))
    parts = []

    rank = _mlb_rank_pitching('era', value, higher_is_better=False)
    if rank and rank <= 15:
        parts.append(f'{_ord(rank)} in MLB in ERA')

    best_val, best_yr = _career_high_pitching(pid, 'era', higher_is_better=False)
    if best_val is not None:
        if value and value < best_val:
            parts.append(f'career best (prev best: {best_val} ERA in {best_yr})')
        else:
            parts.append(f'career best ERA was {best_val} ({best_yr})')

    return ' · '.join(parts)


def _streak_context(story):
    value = story.get('value', 0)
    stat  = story.get('stat', '')
    if stat == 'hits':
        return f'{value}-game hitting streak (active)'
    if stat == 'reached_base':
        return f'{value}-game on-base streak (active)'
    return ''


def career_batting(player_id, stat_col, higher_is_better=True):
    """Public wrapper for caption writers."""
    return _career_high_batting(str(player_id), stat_col, higher_is_better)

def career_pitching(player_id, stat_col, higher_is_better=False):
    """Public wrapper for caption writers."""
    return _career_high_pitching(str(player_id), stat_col, higher_is_better)


def build_digest_context(story) -> str:
    """Return a one-line context string for a digest entry, or '' if none."""
    try:
        story_type = story.get('type', '')
        if story_type == 'pace':
            return _pace_context(story)
        if story_type == 'outlier_ops':
            return _outlier_ops_context(story)
        if story_type == 'outlier_avg':
            return _outlier_avg_context(story)
        if story_type == 'outlier_era':
            return _outlier_era_context(story)
        if story_type in ('hitting_streak', 'onbase_streak'):
            return _streak_context(story)
    except Exception:
        pass
    return ''
