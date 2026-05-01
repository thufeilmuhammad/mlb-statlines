# ══════════════════════════════════════
# FULL COUNT — CONFIG
# ══════════════════════════════════════

IG_HANDLE = "@FullCountID"
ACCOUNT_NAME = "FULL COUNT"

CARD_WIDTH = 1080
CARD_HEIGHT = 1080

FONT_SERIF = "Georgia"
FONT_SANS  = "Arial"

# ── TEAM COLOR MAP ──
# primary  = background color (most distinctive team color)
# secondary = accent color (used for borders, topbar, stat values)
# text      = 'light' (white text) or 'dark' (black text) based on primary bg luminance

TEAM_COLORS = {
    # AL EAST
    'NYY': {'primary': '#132448', 'secondary': '#C4CED3', 'text': 'light'},  # navy / grey
    'BOS': {'primary': '#BD3039', 'secondary': '#192C55', 'text': 'light'},  # red / navy
    'BAL': {'primary': '#DF4601', 'secondary': '#000000', 'text': 'dark'},   # orange / black
    'TBR': {'primary': '#092C5C', 'secondary': '#8FBCE6', 'text': 'light'},  # navy / light blue
    'TOR': {'primary': '#134A8E', 'secondary': '#E8291C', 'text': 'light'},  # blue / red

    # AL CENTRAL
    'CWS': {'primary': '#27251F', 'secondary': '#C4CED4', 'text': 'light'},  # black / silver
    'CLE': {'primary': '#00385D', 'secondary': '#E50022', 'text': 'light'},  # navy / red
    'DET': {'primary': '#182D55', 'secondary': '#F26722', 'text': 'light'},  # navy / orange
    'KCR': {'primary': '#174885', 'secondary': '#C0995A', 'text': 'light'},  # blue / gold
    'MIN': {'primary': '#002B5C', 'secondary': '#D31145', 'text': 'light'},  # navy / red

    # AL WEST
    'HOU': {'primary': '#002D62', 'secondary': '#EB6E1F', 'text': 'light'},  # navy / orange
    'LAA': {'primary': '#BA0021', 'secondary': '#003263', 'text': 'light'},  # red / navy
    'OAK': {'primary': '#003831', 'secondary': '#EFB21E', 'text': 'light'},  # green / gold
    'ATH': {'primary': '#003831', 'secondary': '#EFB21E', 'text': 'light'},  # green / gold
    'SEA': {'primary': '#0C2C56', 'secondary': '#005C5C', 'text': 'light'},  # navy / green
    'TEX': {'primary': '#003278', 'secondary': '#C0111F', 'text': 'light'},  # blue / red

    # NL EAST
    'ATL': {'primary': '#13274F', 'secondary': '#CE1141', 'text': 'light'},  # navy / red
    'MIA': {'primary': '#000000', 'secondary': '#0077C8', 'text': 'light'},  # black / blue
    'NYM': {'primary': '#002D72', 'secondary': '#FF5910', 'text': 'light'},  # blue / orange
    'PHI': {'primary': '#E81828', 'secondary': '#284898', 'text': 'light'},  # red / blue
    'WSN': {'primary': '#AB0003', 'secondary': '#14225A', 'text': 'light'},  # red / navy

    # NL CENTRAL
    'CHC': {'primary': '#0E3386', 'secondary': '#CC3433', 'text': 'light'},  # blue / red
    'CIN': {'primary': '#C6011F', 'secondary': '#000000', 'text': 'light'},  # red / black
    'MIL': {'primary': '#0A2351', 'secondary': '#B6922E', 'text': 'light'},  # navy / gold
    'PIT': {'primary': '#FDB827', 'secondary': '#000000', 'text': 'dark'},   # gold / black
    'STL': {'primary': '#C41E3A', 'secondary': '#22205F', 'text': 'light'},  # red / navy

    # NL WEST
    'ARI': {'primary': '#A71930', 'secondary': '#E3D4AD', 'text': 'light'},  # red / sand
    'COL': {'primary': '#33006F', 'secondary': '#C4CED4', 'text': 'light'},  # purple / silver
    'LAD': {'primary': '#005A9C', 'secondary': '#EF3E42', 'text': 'light'},  # blue / red
    'SDP': {'primary': '#002D62', 'secondary': '#FFC425', 'text': 'light'},  # navy / gold
    'SFG': {'primary': '#FD5A1E', 'secondary': '#000000', 'text': 'dark'},   # orange / black
}

def get_team_colors(team_abbr):
    return TEAM_COLORS.get(team_abbr, {
        'primary': '#1a1a2e',
        'secondary': '#ffffff',
        'text': 'light'
    })
