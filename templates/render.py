import os
import datetime
from config import get_team_colors, IG_HANDLE, ACCOUNT_NAME

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'graphics', 'output')

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def luminance(hex_color):
    r, g, b = hex_to_rgb(hex_color)
    return 0.299 * r + 0.587 * g + 0.114 * b

def render_html_to_image(html_content, output_path):
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1080, 'height': 1400})
        page.set_content(html_content, wait_until='networkidle')
        page.wait_for_timeout(800)
        card = page.query_selector('.card')
        box  = card.bounding_box()
        page.screenshot(path=output_path, clip={
            'x': box['x'], 'y': box['y'],
            'width': box['width'], 'height': box['height']
        })
        browser.close()
    print(f"Graphic saved: {output_path}")
    return output_path

def build_pace_html(story):
    team      = story.get('team', '')
    colors    = get_team_colors(team)
    primary   = colors['primary']
    secondary = colors['secondary']
    is_light  = luminance(primary) > 128

    sr, sg, sb = hex_to_rgb(secondary)

    # Area fill — use secondary if high contrast, else use text color
    sec_lum = luminance(secondary)
    pri_lum = luminance(primary)
    if abs(sec_lum - pri_lum) < 60:
        ar, ag, ab = (0,0,0) if is_light else (255,255,255)
    else:
        ar, ag, ab = sr, sg, sb

    def tc(a):
        return f'rgba(0,0,0,{a})' if is_light else f'rgba(255,255,255,{a})'

    def sc(a):
        return f'rgba({sr},{sg},{sb},{a})'

    text_solid = '#000000' if is_light else '#ffffff'

    current    = story['value']
    projected  = story['projected']
    games      = story['games_played']
    record     = story['record']
    stat_lbl   = story['stat_label']
    lede       = story.get('lede', f"{current} {stat_lbl} through {games} games. The single-season record is {record}.")
    context    = story.get('context', f"The all-time single-season record is {record}. At this pace, {story['entity_name']} is tracking one of the most remarkable individual seasons in baseball history.")

    today_str  = datetime.date.today().strftime('%B %d, %Y').upper()
    chart_ymax = round(max(projected, record) * 1.08)

    team_names = {
        'NYY':'New York Yankees','BOS':'Boston Red Sox','BAL':'Baltimore Orioles',
        'TBR':'Tampa Bay Rays','TOR':'Toronto Blue Jays','HOU':'Houston Astros',
        'LAA':'LA Angels','SEA':'Seattle Mariners','OAK':'Oakland Athletics',
        'ATH':'Athletics','TEX':'Texas Rangers','CLE':'Cleveland Guardians',
        'CWS':'Chicago White Sox','DET':'Detroit Tigers','KCR':'Kansas City Royals',
        'MIN':'Minnesota Twins','NYM':'New York Mets','ATL':'Atlanta Braves',
        'MIA':'Miami Marlins','PHI':'Philadelphia Phillies','WSN':'Washington Nationals',
        'CHC':'Chicago Cubs','CIN':'Cincinnati Reds','MIL':'Milwaukee Brewers',
        'PIT':'Pittsburgh Pirates','STL':'St. Louis Cardinals','ARI':'Arizona Diamondbacks',
        'COL':'Colorado Rockies','LAD':'Los Angeles Dodgers','SDP':'San Diego Padres',
        'SFG':'San Francisco Giants',
    }
    team_full = team_names.get(team, team)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1080px;
    background: {primary};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }}
  .card {{
    width: 1080px;
    display: flex; flex-direction: column;
    overflow: hidden;
  }}
  .topbar {{ height: 6px; background: {secondary}; }}
  .masthead {{
    padding: 20px 44px 16px;
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid {sc(0.3)};
  }}
  .pub {{
    font-size: 28px; font-weight: 700;
    letter-spacing: 0.18em; font-family: 'Georgia', serif;
    color: {text_solid};
  }}
  .meta {{ font-size: 17px; color: {tc(0.5)}; letter-spacing: 0.06em; }}
  .inner {{
    padding: 22px 44px 0;
    display: flex; flex-direction: column;
  }}
  .eyebrow {{
    font-size: 17px; color: {tc(0.5)};
    letter-spacing: 0.14em; text-transform: uppercase;
    margin-bottom: 10px;
  }}
  .headline {{
    font-size: 52px; font-weight: 700;
    font-family: 'Georgia', serif; color: {text_solid};
    line-height: 1.1; margin-bottom: 14px;
    padding-bottom: 14px; border-bottom: 1px solid {sc(0.3)};
  }}
  .lede {{
    font-size: 19px; color: {tc(0.65)};
    font-style: italic; line-height: 1.55;
    margin-bottom: 20px;
  }}
  .stat-row {{ display: flex; gap: 14px; margin-bottom: 20px; }}
  .sc {{
    flex: 1; border-radius: 6px; padding: 18px 22px 14px;
    border: 1px solid {sc(0.45)};
    background: {sc(0.12)};
  }}
  .sc-val {{
    font-size: 60px; font-weight: 700;
    font-family: 'Georgia', serif;
    color: {text_solid}; line-height: 1;
  }}
  .sc-label {{
    font-size: 15px; color: {tc(0.45)};
    text-transform: uppercase; letter-spacing: 0.07em;
    margin-top: 6px; line-height: 1.4;
  }}
  .chart-wrap {{ margin-bottom: 20px; }}
  .chart-label {{
    font-size: 15px; color: {tc(0.38)};
    text-transform: uppercase; letter-spacing: 0.09em;
    margin-bottom: 8px;
  }}
  .context {{
    font-size: 18px; color: {tc(0.62)}; line-height: 1.65;
    border-left: 4px solid {sc(0.8)};
    padding-left: 16px;
    margin-bottom: 22px;
  }}
  .footer {{
    padding: 14px 44px;
    display: flex; justify-content: space-between; align-items: center;
    border-top: 1px solid {sc(0.25)};
    background: {sc(0.08)};
  }}
  .footer-text {{ font-size: 15px; color: {tc(0.3)}; letter-spacing: 0.06em; }}
</style>
</head>
<body>
<div class="card">
  <div class="topbar"></div>
  <div class="masthead">
    <div class="pub">{ACCOUNT_NAME}</div>
    <div class="meta">{today_str} &nbsp;·&nbsp; PACE TRACKER</div>
  </div>
  <div class="inner">
    <div class="eyebrow">{team_full} &nbsp;·&nbsp; {story['entity_name']}</div>
    <div class="headline">{story['label']}</div>
    <div class="lede">{lede}</div>
    <div class="stat-row">
      <div class="sc">
        <div class="sc-val">{current}</div>
        <div class="sc-label">{stat_lbl}<br>through {games} games</div>
      </div>
      <div class="sc">
        <div class="sc-val">{projected}</div>
        <div class="sc-label">Full season<br>projection</div>
      </div>
      <div class="sc">
        <div class="sc-val">{record}</div>
        <div class="sc-label">Single season<br>record</div>
      </div>
    </div>
    <div class="chart-wrap">
      <div class="chart-label">{stat_lbl} pace vs single-season record</div>
      <canvas id="chart" width="992" height="200"></canvas>
    </div>
    <div class="context">{context}</div>
  </div>
  <div class="footer">
    <div class="footer-text">{IG_HANDLE}</div>
    <div class="footer-text">MLB STATS API · BASEBALL REFERENCE</div>
  </div>
</div>
<script>
(function() {{
  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const pad = {{ l: 44, r: 16, t: 16, b: 28 }};
  const cW = W - pad.l - pad.r;
  const cH = H - pad.t - pad.b;
  const current   = {current};
  const projected = {projected};
  const games     = {games};
  const record    = {record};
  const total     = 162;
  const yMax      = {chart_ymax};
  const toX = g => pad.l + (g / total) * cW;
  const toY = v => pad.t + cH - (v / yMax) * cH;

  [0, Math.round(yMax*0.33), Math.round(yMax*0.66)].forEach(v => {{
    ctx.strokeStyle = '{sc(0.15)}'; ctx.lineWidth = 0.5;
    ctx.beginPath(); ctx.moveTo(pad.l, toY(v)); ctx.lineTo(pad.l+cW, toY(v)); ctx.stroke();
    ctx.fillStyle = '{tc(0.3)}'; ctx.font = '14px sans-serif'; ctx.textAlign = 'right';
    ctx.fillText(v, pad.l-6, toY(v)+4);
  }});

  ctx.strokeStyle = '{tc(0.4)}'; ctx.lineWidth = 1.5; ctx.setLineDash([8,5]);
  ctx.beginPath(); ctx.moveTo(pad.l, toY(record)); ctx.lineTo(pad.l+cW, toY(record)); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = '{tc(0.45)}'; ctx.font = '14px sans-serif'; ctx.textAlign = 'left';
  ctx.fillText('{record} record', pad.l+4, toY(record)-7);

  const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t+cH);
  grad.addColorStop(0, 'rgba({ar},{ag},{ab},0.35)');
  grad.addColorStop(1, 'rgba({ar},{ag},{ab},0.02)');
  ctx.beginPath();
  ctx.moveTo(toX(0), pad.t+cH);
  for (let i=0; i<=games; i++) ctx.lineTo(toX(i), toY(i*current/games));
  ctx.lineTo(toX(games), pad.t+cH);
  ctx.closePath();
  ctx.fillStyle = grad; ctx.fill();

  ctx.strokeStyle = '{text_solid}'; ctx.lineWidth = 3;
  ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  ctx.beginPath();
  for (let i=0; i<=games; i++) {{
    i===0 ? ctx.moveTo(toX(i),toY(i*current/games)) : ctx.lineTo(toX(i),toY(i*current/games));
  }}
  ctx.stroke();

  ctx.strokeStyle = '{text_solid}'; ctx.lineWidth = 2;
  ctx.setLineDash([8,5]); ctx.globalAlpha = 0.4;
  ctx.beginPath();
  for (let i=0; i<=total-games; i++) {{
    const g=games+i, val=current+i*(projected-current)/(total-games);
    i===0 ? ctx.moveTo(toX(g),toY(val)) : ctx.lineTo(toX(g),toY(val));
  }}
  ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha=1.0;

  ctx.beginPath(); ctx.arc(toX(games),toY(current),10,0,Math.PI*2);
  ctx.fillStyle='{text_solid}'; ctx.fill();
  ctx.beginPath(); ctx.arc(toX(games),toY(current),5,0,Math.PI*2);
  ctx.fillStyle='{primary}'; ctx.fill();

  ctx.fillStyle='{tc(0.38)}'; ctx.font='14px sans-serif';
  ctx.globalAlpha=1.0; ctx.textAlign='center';
  [[0,'G1'],[54,'G54'],[games,`G{games}`],[108,'G108'],[162,'G162']].forEach(([g,lbl])=>{{
    ctx.fillText(lbl,toX(g),pad.t+cH+20);
  }});
}})();
</script>
</body>
</html>"""
    return html

def render_story(story, output_filename=None):
    html = build_pace_html(story)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not output_filename:
        output_filename = f"{story['type']}_{story['entity_id']}_{datetime.date.today()}.png"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    return render_html_to_image(html, output_path)

if __name__ == '__main__':
    from engine.detectors import run_all_detectors
    from engine.scorer import rank_candidates
    candidates = run_all_detectors()
    top = rank_candidates(candidates)
    if top:
        story = top[0]
        print(f"Rendering: {story['entity_name']} — {story['label']}")
        path = render_story(story)
        import subprocess
        subprocess.run(['open', path])
