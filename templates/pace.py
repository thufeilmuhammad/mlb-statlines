from PIL import Image, ImageDraw, ImageFont
import os
import datetime
from config import get_team_colors, CARD_WIDTH, CARD_HEIGHT, IG_HANDLE, ACCOUNT_NAME

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'graphics', 'output')

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgba(hex_color, alpha=255):
    r, g, b = hex_to_rgb(hex_color)
    return (r, g, b, alpha)

def get_font(size, bold=False):
    font_names = ['Georgia', 'Arial', 'Helvetica']
    for name in font_names:
        paths = [
            f'/System/Library/Fonts/{name}.ttf',
            f'/System/Library/Fonts/Supplemental/{name}.ttf',
            f'/Library/Fonts/{name}.ttf',
        ]
        for path in paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except:
                    continue
    return ImageFont.load_default()

def draw_rounded_rect(draw, xy, radius, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill)
    draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill)
    draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill)
    draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill)

def draw_pace_chart(draw, story, x, y, w, h, line_color, grid_color, axis_color, label_font):
    current = story['value']
    projected = story['projected']
    games_played = story['games_played']
    record = story['record']
    total_games = 162
    pad_l, pad_r, pad_t, pad_b = 50, 20, 20, 30
    cw = w - pad_l - pad_r
    ch = h - pad_t - pad_b
    y_max = max(projected, record) * 1.1

    def to_px(gx, gy):
        px = x + pad_l + int(gx / total_games * cw)
        py = y + pad_t + ch - int(gy / y_max * ch)
        return px, py

    grid_steps = [0, int(y_max * 0.25), int(y_max * 0.5), int(y_max * 0.75)]
    for val in grid_steps:
        gx1, gy1 = to_px(0, val)
        gx2, gy2 = to_px(total_games, val)
        draw.line([(gx1, gy1), (gx2, gy2)], fill=grid_color, width=1)
        draw.text((x + pad_l - 6, gy1), str(val), font=label_font, fill=axis_color, anchor='rm')

    rx1, ry1 = to_px(0, record)
    rx2, ry2 = to_px(total_games, record)
    for i in range(0, int(rx2 - rx1), 16):
        draw.line([(rx1 + i, ry1), (min(rx1 + i + 8, rx2), ry1)], fill=axis_color, width=2)
    draw.text((rx1 + 4, ry1 - 14), f"{record} record", font=label_font, fill=axis_color)

    actual_pts = [(to_px(i, int(i * current / games_played))) for i in range(games_played + 1)]
    for i in range(len(actual_pts) - 1):
        draw.line([actual_pts[i], actual_pts[i+1]], fill=line_color, width=4)

    proj_pts = []
    for i in range(total_games - games_played + 1):
        g = games_played + i
        val = current + int(i * (projected - current) / (total_games - games_played))
        proj_pts.append(to_px(g, val))
    for i in range(len(proj_pts) - 1):
        draw.line([proj_pts[i], proj_pts[i+1]], fill=line_color[:3] + (100,), width=3)

    tx, ty = to_px(games_played, current)
    draw.ellipse([(tx-8, ty-8), (tx+8, ty+8)], fill=line_color)

    for g, lbl in [(0, 'G1'), (54, 'G54'), (games_played, f'G{games_played}'), (108, 'G108'), (162, 'G162')]:
        px, py = to_px(g, 0)
        draw.text((px, y + pad_t + ch + 8), lbl, font=label_font, fill=axis_color, anchor='mt')

def render_pace_card(story, output_filename=None):
    team = story.get('team', '')
    colors = get_team_colors(team)
    primary = colors['primary']
    secondary = colors['secondary']
    is_dark = colors['text'] == 'light'

    def tc(opacity=1.0):
        base = (255, 255, 255) if is_dark else (0, 0, 0)
        return base + (int(opacity * 255),)

    def sc(opacity=1.0):
        r, g, b = hex_to_rgb(secondary)
        return (r, g, b, int(opacity * 255))

    W, H = CARD_WIDTH, CARD_HEIGHT
    img = Image.new('RGBA', (W, H), rgba(primary))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (W, 6)], fill=hex_to_rgb(secondary) + (255,))

    mast_font = get_font(52, bold=True)
    meta_font = get_font(26)
    draw.text((56, 30), ACCOUNT_NAME, font=mast_font, fill=tc(1.0))
    today = datetime.date.today().strftime('%B %d, %Y').upper()
    draw.text((W - 56, 30), f"{today}  ·  PACE TRACKER", font=meta_font, fill=tc(0.5), anchor='rt')
    draw.line([(56, 100), (W - 56, 100)], fill=sc(0.25), width=1)

    eyebrow_font = get_font(26)
    eyebrow = f"{story.get('team', '')}  ·  {story['entity_name'].upper()}"
    draw.text((56, 118), eyebrow, font=eyebrow_font, fill=tc(0.5))

    headline_font = get_font(68, bold=True)
    headline = story['label']
    words = headline.split()
    lines = []
    current_line = []
    for word in words:
        test = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test, font=headline_font)
        if bbox[2] - bbox[0] > W - 112:
            lines.append(' '.join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(' '.join(current_line))

    hl_y = 158
    for line in lines:
        draw.text((56, hl_y), line, font=headline_font, fill=tc(1.0))
        hl_y += 78

    draw.line([(56, hl_y + 10), (W - 56, hl_y + 10)], fill=sc(0.2), width=1)

    lede_font = get_font(30)
    lede = f"{story['value']} {story['stat_label']} through {story['games_played']} games. The single-season record is {story['record']}."
    draw.text((56, hl_y + 26), lede, font=lede_font, fill=tc(0.6))

    box_y = hl_y + 90
    box_h = 130
    box_gap = 16
    box_w = (W - 112 - box_gap * 2) // 3
    stat_num_font = get_font(72, bold=True)
    stat_label_font = get_font(22)

    stats = [
        (str(story['value']), f"{story['stat_label'].upper()}\nTHROUGH {story['games_played']} GAMES"),
        (str(story['projected']), f"FULL SEASON\nPROJECTION"),
        (str(story['record']), f"SINGLE SEASON\nRECORD"),
    ]

    for i, (num, label) in enumerate(stats):
        bx = 56 + i * (box_w + box_gap)
        by = box_y
        draw_rounded_rect(draw, (bx, by, bx + box_w, by + box_h), 8, sc(0.08))
        draw.rectangle([(bx, by), (bx + box_w, by + box_h)], outline=sc(0.18), width=1)
        draw.text((bx + 18, by + 14), num, font=stat_num_font, fill=sc(1.0))
        for j, lbl_line in enumerate(label.split('\n')):
            draw.text((bx + 18, by + box_h - 44 + j * 20), lbl_line, font=stat_label_font, fill=tc(0.4))

    chart_y = box_y + box_h + 30
    chart_h = 200
    draw.text((56, chart_y - 24), f"{story['stat_label'].upper()} PACE VS RECORD", font=get_font(22), fill=tc(0.38))
    draw_pace_chart(draw, story, 56, chart_y, W - 112, chart_h, tc(0.9), sc(0.12), tc(0.3), get_font(22))

    context_y = chart_y + chart_h + 20
    draw.rectangle([(56, context_y), (60, context_y + 48)], fill=sc(0.4))
    context_font = get_font(28)
    diff = story['projected'] - story['record']
    if diff >= 0:
        context = f"At this pace, {story['entity_name']} would break the all-time record by {diff}."
    else:
        context = f"At this pace, {story['entity_name']} would finish {abs(diff)} short of the all-time record."
    draw.text((72, context_y + 6), context, font=context_font, fill=tc(0.55))

    footer_y = H - 52
    draw.line([(56, footer_y - 10), (W - 56, footer_y - 10)], fill=sc(0.15), width=1)
    footer_font = get_font(24)
    draw.text((56, footer_y), IG_HANDLE, font=footer_font, fill=tc(0.3))
    draw.text((W - 56, footer_y), "MLB STATS API · BASEBALL REFERENCE", font=footer_font, fill=tc(0.3), anchor='rt')

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not output_filename:
        output_filename = f"pace_{story['entity_id']}_{datetime.date.today()}.png"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    img = img.convert('RGB')
    img.save(output_path, 'PNG', quality=95)
    print(f"Graphic saved: {output_path}")
    return output_path

if __name__ == '__main__':
    from engine.detectors import run_all_detectors
    from engine.scorer import rank_candidates
    candidates = run_all_detectors()
    top = rank_candidates(candidates)
    if top:
        story = top[0]
        print(f"Rendering: {story['entity_name']} — {story['label']}")
        path = render_pace_card(story)
        print(f"Done: {path}")
        import subprocess
        subprocess.run(['open', path])
