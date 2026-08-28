import os
import sys
import json
import math
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np

# Paths
ASSETS_DIR = "assets"
GENERATED_DIR = os.path.join(ASSETS_DIR, "generated")
DATA_FILE = os.path.join(GENERATED_DIR, "contribution-data.json")
OUTPUT_GIF = os.path.join(GENERATED_DIR, "mario-github.gif")

# Viewport dimensions (Clean widescreen presentation for GitHub profile)
VIEW_W = 760
VIEW_H = 280
FPS = 14

# GitHub Dark Theme Color Palette
BG_COLOR = (13, 17, 23)        # #0d1117 canvas
HUD_BG = (22, 27, 34)          # #161b22 HUD card
BORDER_COLOR = (48, 54, 61)    # #30363d borders
BORDER_SUBTLE = (33, 38, 45)   # #21262d cell borders
TEXT_WHITE = (240, 246, 252)   # #f0f6fc
TEXT_MUTED = (139, 148, 158)   # #8b949e
TEXT_GOLD = (242, 204, 96)     # Arcade gold #f2cc60
TEXT_FIRE = (255, 140, 0)      # Streak orange

# Authentic GitHub Contribution Heatmap Colors
COLOR_ZERO = (22, 27, 34)        # Level 0 (#161b22 dark empty)
COLOR_LEVEL1 = (14, 68, 41)      # Level 1 (#0e4429 dark green)
COLOR_LEVEL2 = (0, 109, 50)      # Level 2 (#006d32 emerald green)
COLOR_LEVEL3 = (38, 166, 65)     # Level 3 (#26a641 bright green)
COLOR_LEVEL4 = (57, 211, 83)     # Level 4 (#39d353 vibrant green)

BORDER_ZERO = (33, 38, 45)       # Level 0 border
BORDER_LEVEL1 = (18, 90, 54)     # Level 1 border
BORDER_LEVEL2 = (0, 140, 64)     # Level 2 border
BORDER_LEVEL3 = (46, 190, 78)    # Level 3 border
BORDER_LEVEL4 = (86, 240, 114)   # Level 4 border

# Space & Corridor Platform Colors
RAIL_TOP = (35, 134, 54)         # Subtle GitHub green guide rail
RAIL_BODY = (22, 27, 34)         # Platform girder
RAIL_BORDER = (48, 54, 61)
PIPE_GREEN = (46, 160, 67)       # Warp pipe green
PIPE_DARK = (24, 86, 36)
FLAGPOLE_COLOR = (139, 148, 158)

def get_font(size, bold=False):
    font_candidates = [
        'arialbd.ttf' if bold else 'arial.ttf',
        'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf',
        'FreeSansBold.ttf' if bold else 'FreeSans.ttf',
        'segoeui.ttf'
    ]
    for fn in font_candidates:
        try:
            return ImageFont.truetype(fn, size)
        except IOError:
            continue
    return ImageFont.load_default()

def remove_white_bg(img, dist_thresh=35):
    img = img.convert("RGBA")
    arr = np.array(img)
    r, g, b = arr[:, :, 0].astype(float), arr[:, :, 1].astype(float), arr[:, :, 2].astype(float)
    dist = np.sqrt((255.0 - r)**2 + (255.0 - g)**2 + (255.0 - b)**2)
    transparent = dist < dist_thresh
    semi = (dist >= dist_thresh) & (dist < dist_thresh + 25)
    arr[transparent, 3] = 0
    arr[semi, 3] = ((dist[semi] - dist_thresh) / 25.0 * 255).astype(np.uint8)
    res = Image.fromarray(arr)
    bbox = res.getbbox()
    return res.crop(bbox) if bbox else res

def create_flame_sprite(width=11, height=14):
    # Supersampled 3-tier organic flame icon with smooth anti-aliased curves
    scale = 4
    sw, sh = width * scale, height * scale
    im = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    
    # Outer flame (Vibrant flame red-orange)
    outer_pts = [
        (sw * 0.50, sh * 0.05),
        (sw * 0.64, sh * 0.28),
        (sw * 0.82, sh * 0.18),
        (sw * 0.74, sh * 0.45),
        (sw * 0.94, sh * 0.65),
        (sw * 0.86, sh * 0.86),
        (sw * 0.50, sh * 0.98),
        (sw * 0.14, sh * 0.86),
        (sw * 0.06, sh * 0.65),
        (sw * 0.26, sh * 0.45),
        (sw * 0.18, sh * 0.25),
        (sw * 0.36, sh * 0.30),
    ]
    d.polygon(outer_pts, fill=(255, 69, 0, 255))
    
    # Mid flame (Warm orange)
    mid_pts = [
        (sw * 0.50, sh * 0.20),
        (sw * 0.62, sh * 0.38),
        (sw * 0.74, sh * 0.42),
        (sw * 0.82, sh * 0.66),
        (sw * 0.74, sh * 0.84),
        (sw * 0.50, sh * 0.92),
        (sw * 0.26, sh * 0.84),
        (sw * 0.18, sh * 0.66),
        (sw * 0.30, sh * 0.45),
        (sw * 0.38, sh * 0.38),
    ]
    d.polygon(mid_pts, fill=(255, 145, 0, 255))
    
    # Inner flame core (Bright glowing golden-yellow)
    inner_pts = [
        (sw * 0.50, sh * 0.42),
        (sw * 0.64, sh * 0.64),
        (sw * 0.58, sh * 0.84),
        (sw * 0.50, sh * 0.88),
        (sw * 0.42, sh * 0.84),
        (sw * 0.36, sh * 0.64),
    ]
    d.polygon(inner_pts, fill=(255, 225, 45, 255))
    
    return im.resize((width, height), Image.Resampling.LANCZOS)

def load_sprites():
    # Scale Mario to match authentic ~12px GitHub contribution cells
    # Mario: width 20, height 26
    idle_raw = Image.open(os.path.join(ASSETS_DIR, "mario.png")).convert("RGBA")
    bbox = idle_raw.getbbox()
    idle_raw = idle_raw.crop(bbox) if bbox else idle_raw
    mario_idle_r = idle_raw.resize((20, 26), Image.Resampling.LANCZOS)
    mario_idle_l = ImageOps.mirror(mario_idle_r)

    # Running Leg 1: Left leg forward, right leg back (from mario.png)
    mario_run1_r = idle_raw.resize((21, 26), Image.Resampling.LANCZOS)
    mario_run1_l = ImageOps.mirror(mario_run1_r)

    # Running Leg 2: Right leg forward, left leg back (from running mario.jpg)
    run_raw = Image.open(os.path.join(ASSETS_DIR, "running mario.jpg"))
    run_clean = remove_white_bg(run_raw)
    mario_run2_r = run_clean.resize((21, 26), Image.Resampling.LANCZOS)
    mario_run2_l = ImageOps.mirror(mario_run2_r)

    hit_raw = Image.open(os.path.join(ASSETS_DIR, "hitting coin.jpg"))
    hw, hh = hit_raw.size
    hit_crop = hit_raw.crop((0, int(hh * 0.36), hw, hh))
    hit_clean = remove_white_bg(hit_crop)
    mario_hit_r = hit_clean.resize((21, 28), Image.Resampling.LANCZOS)
    mario_hit_l = ImageOps.mirror(mario_hit_r)

    mario_slide_r = mario_idle_r.resize((18, 25), Image.Resampling.LANCZOS)
    mario_slide_l = ImageOps.mirror(mario_slide_r)

    coin_raw = Image.open(os.path.join(ASSETS_DIR, "coin.webp")).convert("RGBA")
    c_bbox = coin_raw.getbbox()
    coin_sprite = coin_raw.resize((12, 15), Image.Resampling.LANCZOS)
    coin_small = coin_raw.resize((10, 12), Image.Resampling.LANCZOS)
    fire_path = os.path.join(ASSETS_DIR, "fire_emoji.png")
    if os.path.exists(fire_path):
        fire_raw = Image.open(fire_path).convert("RGBA")
        flame_sprite = fire_raw.resize((12, 14), Image.Resampling.LANCZOS)
    else:
        flame_sprite = create_flame_sprite(11, 14)

    return {
        "idle_r": mario_idle_r,
        "idle_l": mario_idle_l,
        "run1_r": mario_run1_r,
        "run1_l": mario_run1_l,
        "run2_r": mario_run2_r,
        "run2_l": mario_run2_l,
        "hit_r": mario_hit_r,
        "hit_l": mario_hit_l,
        "slide_r": mario_slide_r,
        "slide_l": mario_slide_l,
        "coin": coin_sprite,
        "coin_small": coin_small,
        "flame": flame_sprite
    }

def get_block_colors(level, cnt):
    if cnt == 0 or level == 0:
        return COLOR_ZERO, BORDER_ZERO
    elif level == 1 or cnt <= 2:
        return COLOR_LEVEL1, BORDER_LEVEL1
    elif level == 2 or cnt <= 5:
        return COLOR_LEVEL2, BORDER_LEVEL2
    elif level == 3 or cnt <= 8:
        return COLOR_LEVEL3, BORDER_LEVEL3
    else:
        return COLOR_LEVEL4, BORDER_LEVEL4

def draw_star(draw, cx, cy, r_outer, r_inner, fill_color, outline_color=None):
    points = []
    for i in range(10):
        r = r_outer if i % 2 == 0 else r_inner
        angle = i * math.pi / 5.0 - math.pi / 2.0
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=fill_color, outline=outline_color)

def build_world_layout(data):
    num_weeks = data["num_weeks"]
    
    # Authentic GitHub Heatmap Proportions:
    # 12px cell, 3px gap, radius 2px
    CELL_SIZE = 12
    CELL_RADIUS = 2
    COL_GAP = 3
    COL_PITCH = CELL_SIZE + COL_GAP  # 15px per week column
    
    LEFT_PAD = 80
    RIGHT_PAD = 100
    
    WORLD_W = LEFT_PAD + num_weeks * COL_PITCH + RIGHT_PAD
    
    TOP_PAD = 55
    ROW_PITCH = 56       # Generous corridor space: Mario runs with 14px headroom
    
    WORLD_H = TOP_PAD + 7 * ROW_PITCH + 35
    
    cell_coords = [[(0, 0) for _ in range(num_weeks)] for _ in range(7)]
    corridor_floors = []
    
    for r in range(7):
        block_y = TOP_PAD + r * ROW_PITCH + 6
        # Mario height 26, block height 12. Floor at block_y + 12 + 14 + 26 = block_y + 52
        floor_y = block_y + 50
        corridor_floors.append(floor_y)
        for c in range(num_weeks):
            bx = LEFT_PAD + c * COL_PITCH
            cell_coords[r][c] = (bx, block_y)
            
    return {
        "num_weeks": num_weeks,
        "cell_size": CELL_SIZE,
        "cell_radius": CELL_RADIUS,
        "col_gap": COL_GAP,
        "col_pitch": COL_PITCH,
        "left_pad": LEFT_PAD,
        "right_pad": RIGHT_PAD,
        "world_w": WORLD_W,
        "world_h": WORLD_H,
        "top_pad": TOP_PAD,
        "row_pitch": ROW_PITCH,
        "cell_coords": cell_coords,
        "corridor_floors": corridor_floors
    }

def generate_snake_timeline(data, layout):
    grid = data["grid"]
    num_weeks = layout["num_weeks"]
    cell_coords = layout["cell_coords"]
    corridor_floors = layout["corridor_floors"]
    cell_size = layout["cell_size"]
    
    timeline = []
    
    # 1. Intro sequence on Row 0
    start_x = layout["left_pad"] - 25
    r0_floor = corridor_floors[0]
    
    for _ in range(4):
        timeline.append({
            "mario_x": start_x,
            "mario_y": r0_floor - 26,
            "pose": "idle_r",
            "active_hit": None,
            "current_row": 0,
            "current_col": 0,
            "descending": False
        })
        
    curr_x = start_x
    
    for r in range(7):
        row_floor = corridor_floors[r]
        mario_base_y = row_floor - 26
        is_even = (r % 2 == 0)
        direction = 1 if is_even else -1
        
        cols = list(range(num_weeks)) if is_even else list(range(num_weeks - 1, -1, -1))
        
        i = 0
        while i < len(cols):
            c = cols[i]
            cell = grid[r][c]
            bx, by = cell_coords[r][c]
            target_x = bx + (cell_size // 2) - 10  # Centered under 12px cell
            
            is_active = (cell and cell.get("contributions", 0) > 0)
            
            if is_active:
                # Approach smoothly (1 frame decelerating step)
                app_x = curr_x + (target_x - curr_x) * 0.65
                run_pose = f"run{(len(timeline) % 2) + 1}_{'r' if direction == 1 else 'l'}"
                timeline.append({
                    "mario_x": app_x,
                    "mario_y": mario_base_y,
                    "pose": run_pose,
                    "active_hit": None,
                    "current_row": r,
                    "current_col": c,
                    "descending": False
                })
                
                # Jump rise (1 frame midway up)
                mid_jump_y = mario_base_y - 8
                timeline.append({
                    "mario_x": target_x,
                    "mario_y": mid_jump_y,
                    "pose": f"hit_{'r' if direction == 1 else 'l'}",
                    "active_hit": None,
                    "current_row": r,
                    "current_col": c,
                    "descending": False
                })
                
                # HIT IMPACT: Fist touches underside of cell (at by + cell_size)
                # Cell bumps upward by 3px!
                hit_y = by + cell_size - 2
                timeline.append({
                    "mario_x": target_x,
                    "mario_y": hit_y,
                    "pose": f"hit_{'r' if direction == 1 else 'l'}",
                    "active_hit": (r, c),
                    "hit_stage": 0, # Impact + coin emerges
                    "current_row": r,
                    "current_col": c,
                    "descending": False
                })
                
                # Coin floating & Mario descending back to floor
                timeline.append({
                    "mario_x": target_x + direction * 2,
                    "mario_y": mid_jump_y,
                    "pose": f"run1_{'r' if direction == 1 else 'l'}",
                    "active_hit": (r, c),
                    "hit_stage": 1, # Coin floats up
                    "current_row": r,
                    "current_col": c,
                    "descending": False
                })
                
                # Land on corridor floor
                timeline.append({
                    "mario_x": target_x + direction * 4,
                    "mario_y": mario_base_y,
                    "pose": f"run2_{'r' if direction == 1 else 'l'}",
                    "active_hit": None,
                    "current_row": r,
                    "current_col": c,
                    "descending": False
                })
                
                curr_x = target_x + direction * 4
                i += 1
            else:
                # Inactive / empty stretch: Continuous, smooth running (no teleporting!)
                stretch_end = i
                while stretch_end < len(cols):
                    nc = cols[stretch_end]
                    n_cell = grid[r][nc]
                    if n_cell and n_cell.get("contributions", 0) > 0:
                        break
                    stretch_end += 1
                    
                stretch_len = stretch_end - i
                dest_col = cols[stretch_end - 1]
                dest_bx, _ = cell_coords[r][dest_col]
                dest_x = dest_bx + (cell_size // 2) - 10
                
                # Calculate travel distance
                dist = abs(dest_x - curr_x)
                # Pacing: Mario accelerates through long empty stretches (10-12px/frame)
                # and runs at normal comfortable pace (6-7px/frame) near cells.
                # Always continuous with alternating footstep cadence!
                if dist > 40:
                    num_sprint_frames = max(3, int(round(dist / 11.5)))
                else:
                    num_sprint_frames = max(1, int(round(dist / 6.5)))
                
                for sf in range(num_sprint_frames):
                    alpha = (sf + 1) / float(num_sprint_frames)
                    sx = curr_x + (dest_x - curr_x) * alpha
                    s_pose = f"run{(len(timeline) % 2) + 1}_{'r' if direction == 1 else 'l'}"
                    col_index = cols[min(i + int(alpha * stretch_len), len(cols) - 1)]
                    timeline.append({
                        "mario_x": sx,
                        "mario_y": mario_base_y,
                        "pose": s_pose,
                        "active_hit": None,
                        "current_row": r,
                        "current_col": col_index,
                        "descending": False
                    })
                curr_x = dest_x
                i = stretch_end
                
        # End of Row: Edge Turnaround & Smooth Descent to next row
        if r < 6:
            next_floor = corridor_floors[r + 1]
            next_mario_y = next_floor - 26
            
            # Step onto turnaround edge pad
            edge_x = curr_x + direction * 20
            timeline.append({
                "mario_x": edge_x,
                "mario_y": mario_base_y,
                "pose": f"run1_{'r' if direction == 1 else 'l'}",
                "active_hit": None,
                "current_row": r,
                "current_col": cols[-1],
                "descending": False
            })
            
            # Descent: 4 continuous steps down along pipe/ladder
            descend_steps = 4
            for ds in range(descend_steps):
                alpha = (ds + 1) / float(descend_steps)
                dy = mario_base_y + (next_mario_y - mario_base_y) * alpha
                timeline.append({
                    "mario_x": edge_x,
                    "mario_y": dy,
                    "pose": f"slide_{'r' if direction == 1 else 'l'}",
                    "active_hit": None,
                    "current_row": r if alpha < 0.5 else r + 1,
                    "current_col": cols[-1],
                    "descending": True
                })
                
            # Flip orientation on new row
            new_dir = -direction
            timeline.append({
                "mario_x": edge_x,
                "mario_y": next_mario_y,
                "pose": f"idle_{'r' if new_dir == 1 else 'l'}",
                "active_hit": None,
                "current_row": r + 1,
                "current_col": cols[-1],
                "descending": False
            })
            curr_x = edge_x
            
    # Final Victory sequence on Row 6
    flagpole_x = layout["world_w"] - 65
    row6_floor = corridor_floors[6]
    r6_base_y = row6_floor - 26
    
    # Dash to flagpole
    dash_steps = 4
    for step in range(dash_steps):
        ratio = (step + 1) / float(dash_steps)
        fx = curr_x + (flagpole_x - curr_x) * ratio
        timeline.append({
            "mario_x": fx,
            "mario_y": r6_base_y,
            "pose": f"run{(step % 2) + 1}_r",
            "active_hit": None,
            "current_row": 6,
            "current_col": num_weeks - 1,
            "descending": False
        })
        
    # Jump onto flagpole
    timeline.append({
        "mario_x": flagpole_x - 8,
        "mario_y": r6_base_y - 20,
        "pose": "slide_r",
        "active_hit": None,
        "current_row": 6,
        "current_col": num_weeks - 1,
        "descending": False,
        "victory": True
    })
    
    # Slide down
    timeline.append({
        "mario_x": flagpole_x - 8,
        "mario_y": r6_base_y - 4,
        "pose": "slide_r",
        "active_hit": None,
        "current_row": 6,
        "current_col": num_weeks - 1,
        "descending": False,
        "victory": True
    })
    
    # Step off and celebrate
    for v in range(16):
        timeline.append({
            "mario_x": flagpole_x + 12,
            "mario_y": r6_base_y,
            "pose": "hit_r" if v % 4 < 2 else "idle_r",
            "active_hit": None,
            "current_row": 6,
            "current_col": num_weeks - 1,
            "descending": False,
            "victory": True,
            "victory_banner": True
        })
        
    return timeline

def render_world_background(draw, layout, data, font_sub, font_small):
    num_weeks = layout["num_weeks"]
    cell_coords = layout["cell_coords"]
    corridor_floors = layout["corridor_floors"]
    world_w = layout["world_w"]
    left_pad = layout["left_pad"]
    top_pad = layout["top_pad"]
    weekday_names = data.get("weekday_names", ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])

    # 1. Subtle space stars (understated, so heatmap is hero!)
    random.seed(42)
    for _ in range(80):
        sx = random.randint(10, world_w - 10)
        sy = random.randint(10, layout["world_h"] - 10)
        star_color = random.choice([(35, 42, 54), (48, 56, 70), (70, 80, 96)])
        draw.rectangle([sx, sy, sx + 1, sy + 1], fill=star_color)

    # 2. Month labels at top (Sep, Oct, Nov...)
    for ml in data.get("month_labels", []):
        w_idx = ml["week_idx"]
        if w_idx < num_weeks:
            mx, _ = cell_coords[0][w_idx]
            draw.text((mx, top_pad - 18), ml["month"], fill=TEXT_MUTED, font=font_small)

    # 3. Weekday labels and Corridors
    for r in range(7):
        floor_y = corridor_floors[r]
        
        # Weekday Label on left (Sun, Mon...)
        draw.text((left_pad - 42, floor_y - 20), weekday_names[r], fill=TEXT_MUTED, font=font_small)

        # Sleek space rail platform
        draw.rectangle([left_pad - 50, floor_y, world_w - 25, floor_y + 2], fill=RAIL_TOP)
        draw.rectangle([left_pad - 50, floor_y + 2, world_w - 25, floor_y + 5], fill=RAIL_BODY)
        
        for gx in range(left_pad - 50, world_w - 25, 20):
            draw.line([(gx, floor_y + 2), (gx + 3, floor_y + 5)], fill=RAIL_BORDER, width=1)

        # Warp Pipes at edges for descent
        if r < 6:
            next_floor = corridor_floors[r + 1]
            if r % 2 == 0:
                # Right edge pipe
                px = layout["left_pad"] + num_weeks * layout["col_pitch"] + 15
                draw.rectangle([px, floor_y - 8, px + 18, next_floor], fill=PIPE_GREEN, outline=PIPE_DARK, width=1)
                draw.rectangle([px - 2, floor_y - 12, px + 20, floor_y - 6], fill=PIPE_GREEN, outline=PIPE_DARK, width=1)
            else:
                # Left edge pipe
                px = layout["left_pad"] - 32
                draw.rectangle([px, floor_y - 8, px + 18, next_floor], fill=PIPE_GREEN, outline=PIPE_DARK, width=1)
                draw.rectangle([px - 2, floor_y - 12, px + 20, floor_y - 6], fill=PIPE_GREEN, outline=PIPE_DARK, width=1)

    # 4. Final Goal Flagpole on Row 6
    fx = world_w - 65
    r6_floor = corridor_floors[6]
    pole_top_y = r6_floor - 80
    
    draw.line([(fx, pole_top_y), (fx, r6_floor)], fill=FLAGPOLE_COLOR, width=2)
    draw.ellipse([fx - 4, pole_top_y - 8, fx + 4, pole_top_y], fill=TEXT_GOLD)
    draw.polygon([(fx, pole_top_y + 4), (fx - 24, pole_top_y + 16), (fx, pole_top_y + 28)], fill=COLOR_LEVEL3)
    draw_star(draw, fx - 12, pole_top_y + 16, 4, 1.5, TEXT_GOLD)

    # Mini Castle
    cx = fx + 16
    draw.rectangle([cx, r6_floor - 38, cx + 40, r6_floor], fill=(35, 42, 52), outline=BORDER_COLOR)
    for bx in range(cx, cx + 36, 10):
        draw.rectangle([bx, r6_floor - 44, bx + 6, r6_floor - 38], fill=(35, 42, 52), outline=BORDER_COLOR)
    draw.rectangle([cx + 14, r6_floor - 20, cx + 26, r6_floor], fill=(13, 17, 23))

def render_hud(img, draw, font_title, font_sub, font_bold, data, current_coins, total_coins, curr_date, curr_weekday, coin_small, flame_sprite):
    # In-world HUD floating seamlessly on the same dark space background (no separate rectangular panel or border)
    
    # Left: Username only (no game title, no green icon)
    username = data.get("username", "SaitejaKommi")
    draw.text((24, 11), username, fill=TEXT_WHITE, font=font_bold)
    
    # Center: Compact date format (e.g. '24 AUG 2025')
    if curr_date:
        try:
            dt = datetime.strptime(curr_date, "%Y-%m-%d")
            date_str = dt.strftime("%d %b %Y").upper()
        except Exception:
            date_str = curr_date
    else:
        date_str = ""
        
    if date_str:
        draw.text((VIEW_W // 2 - 40, 11), date_str, fill=(180, 190, 205), font=font_sub)
    
    # Right: Real Streak (🔥 Nd without 'STREAK' word) & Dynamic Coins (🪙 current / total)
    streak = data.get("current_streak", 0)
    
    # Clean, organic, 3-layer anti-aliased flame icon + streak
    fx = 556
    img.paste(flame_sprite, (fx, 9), flame_sprite)
    draw.text((fx + 16, 11), f"{streak}d", fill=TEXT_FIRE, font=font_bold)
    
    # Coin icon + counter
    cx = 640
    img.paste(coin_small, (cx, 10), coin_small)
    draw.text((cx + 18, 11), f"{current_coins} / {total_coins}", fill=TEXT_GOLD, font=font_bold)

def render_victory_banner(img, draw, font_title, font_bold, font_sub, total_coins, longest_streak, coin_small):
    bx = VIEW_W // 2 - 190
    by = VIEW_H // 2 - 65
    bw = 380
    bh = 130
    
    draw.rectangle([bx + 3, by + 3, bx + bw + 3, by + bh + 3], fill=(0, 0, 0, 190))
    draw.rectangle([bx, by, bx + bw, by + bh], fill=HUD_BG, outline=TEXT_GOLD, width=2)
    draw.rectangle([bx + 3, by + 3, bx + bw - 3, by + bh - 3], outline=RAIL_TOP, width=1)
    
    draw_star(draw, bx + 26, by + 20, 6, 2.5, TEXT_GOLD)
    draw_star(draw, bx + bw - 26, by + 20, 6, 2.5, TEXT_GOLD)
    
    # Title: YEAR OF BUILDING COMPLETE!
    title_text = "YEAR OF BUILDING COMPLETE!"
    t_bbox = font_title.getbbox(title_text)
    t_w = t_bbox[2] - t_bbox[0] if t_bbox else 200
    draw.text((bx + (bw - t_w) // 2, by + 12), title_text, fill=TEXT_GOLD, font=font_title)
    
    # Coins line: coin icon + FINAL COINS: 628 / 628
    coin_text = f"FINAL COINS: {total_coins} / {total_coins}"
    c_bbox = font_bold.getbbox(coin_text)
    c_w = c_bbox[2] - c_bbox[0] if c_bbox else 140
    total_c_w = 12 + 6 + c_w
    start_c_x = bx + (bw - total_c_w) // 2
    img.paste(coin_small, (start_c_x, by + 45), coin_small)
    draw.text((start_c_x + 18, by + 44), coin_text, fill=TEXT_WHITE, font=font_bold)
    
    # Line 3: GROWTH THROUGH BUILDING | Max Streak: Nd
    line3 = f"GROWTH THROUGH BUILDING | Max Streak: {longest_streak}d"
    l3_bbox = font_bold.getbbox(line3)
    l3_w = l3_bbox[2] - l3_bbox[0] if l3_bbox else 250
    draw.text((bx + (bw - l3_w) // 2, by + 72), line3, fill=TEXT_FIRE, font=font_bold)
    
    # Subtitle: SaitejaKommi's GitHub Year
    sub_text = "SaitejaKommi's GitHub Year"
    sub_bbox = font_sub.getbbox(sub_text)
    sub_w = sub_bbox[2] - sub_bbox[0] if sub_bbox else 150
    draw.text((bx + (bw - sub_w) // 2, by + 98), sub_text, fill=TEXT_MUTED, font=font_sub)

def main():
    print("Generating Authentic GitHub 'The Commit Crush' Animation...")
    if not os.path.exists(DATA_FILE):
        print(f"Data file {DATA_FILE} not found. Run fetch_contributions.py first.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    sprites = load_sprites()
    layout = build_world_layout(data)
    
    font_title = get_font(13, bold=True)
    font_sub = get_font(11, bold=False)
    font_small = get_font(9, bold=False)
    font_bold = get_font(11, bold=True)

    grid = data["grid"]
    num_weeks = layout["num_weeks"]
    cell_coords = layout["cell_coords"]
    cell_size = layout["cell_size"]
    cell_radius = layout["cell_radius"]
    total_coins = data["total_contributions"]
    longest_streak = data.get("longest_streak", 0)

    timeline = generate_snake_timeline(data, layout)
    print(f"Timeline constructed: {len(timeline)} frames.")

    world_bg = Image.new("RGBA", (layout["world_w"], layout["world_h"]), BG_COLOR)
    draw_bg = ImageDraw.Draw(world_bg)
    render_world_background(draw_bg, layout, data, font_sub, font_small)

    hit_state = [[False for _ in range(num_weeks)] for _ in range(7)]
    
    cam_x = 0.0
    cam_y = 0.0
    
    frames = []
    
    for frame_idx, state in enumerate(timeline):
        mx = state["mario_x"]
        my = state["mario_y"]
        pose = state["pose"]
        active_hit = state["active_hit"]
        curr_row = state["current_row"]
        curr_col = state["current_col"]
        
        if active_hit:
            hr, hc = active_hit
            hit_state[hr][hc] = True
            
        current_coins = 0
        for r in range(7):
            for c in range(num_weeks):
                if hit_state[r][c]:
                    cell = grid[r][c]
                    if cell:
                        current_coins += cell.get("contributions", 0)
                        
        # Smooth camera following Mario
        is_even_row = (curr_row % 2 == 0)
        lead_ratio = 0.38 if is_even_row else 0.62
        
        target_cam_x = mx - VIEW_W * lead_ratio
        target_cam_y = my - VIEW_H * 0.52
        
        target_cam_x = max(0, min(layout["world_w"] - VIEW_W, target_cam_x))
        target_cam_y = max(0, min(layout["world_h"] - VIEW_H, target_cam_y))
        
        if frame_idx == 0:
            cam_x = target_cam_x
            cam_y = target_cam_y
        else:
            # Smooth camera tracking
            cam_x += (target_cam_x - cam_x) * 0.35
            cam_y += (target_cam_y - cam_y) * 0.35

        world_frame = world_bg.copy()
        draw_world = ImageDraw.Draw(world_frame)

        # Draw all 7 rows of AUTHENTIC GitHub contribution cells
        for r in range(7):
            for c in range(num_weeks):
                cell = grid[r][c]
                if not cell:
                    continue
                    
                bx, by = cell_coords[r][c]
                cnt = cell.get("contributions", 0)
                lvl = cell.get("level", 0)
                
                curr_by = by
                # Cell bump reaction on hit
                if active_hit == (r, c):
                    hit_stage = state.get("hit_stage", 0)
                    if hit_stage == 0:
                        curr_by = by - 3  # Subtle, physically believable bump
                    else:
                        curr_by = by - 1
                        
                fill_col, border_col = get_block_colors(lvl, cnt)
                
                # Draw rounded rectangle (authentic GitHub look: NO '?' or placeholder symbols!)
                draw_world.rounded_rectangle(
                    [bx, curr_by, bx + cell_size, curr_by + cell_size],
                    radius=cell_radius,
                    fill=fill_col,
                    outline=border_col,
                    width=1
                )

                # Floating coin & contribution badge when hit
                if active_hit == (r, c):
                    hit_stage = state.get("hit_stage", 0)
                    float_y = curr_by - 16 - (hit_stage * 4)
                    coin_s = sprites["coin"]
                    world_frame.paste(coin_s, (int(bx), int(float_y)), coin_s)
                    draw_world.text((bx + 14, float_y), f"+{cnt}", fill=TEXT_GOLD, font=font_bold)

        # Mario
        mario_sprite = sprites.get(pose, sprites["idle_r"])
        world_frame.paste(mario_sprite, (int(mx), int(my)), mario_sprite)

        # Crop Viewport
        int_cam_x = int(round(cam_x))
        int_cam_y = int(round(cam_y))
        viewport = world_frame.crop((int_cam_x, int_cam_y, int_cam_x + VIEW_W, int_cam_y + VIEW_H))
        draw_view = ImageDraw.Draw(viewport)

        curr_cell = grid[curr_row][curr_col] if curr_col < num_weeks else None
        curr_date = curr_cell.get("date", "") if curr_cell else ""
        curr_dayname = data.get("weekday_names", ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])[curr_row]

        # Render HUD
        render_hud(
            viewport, draw_view, font_title, font_sub, font_bold,
            data, current_coins, total_coins, curr_date, curr_dayname, sprites["coin_small"], sprites["flame"]
        )

        # Victory Banner
        if state.get("victory_banner"):
            render_victory_banner(
                viewport, draw_view, font_title, font_bold, font_sub,
                total_coins, longest_streak, sprites["coin_small"]
            )

        frames.append(viewport.convert("RGB"))

    print(f"Rendered {len(frames)} frames. Encoding animated GIF...")

    os.makedirs(GENERATED_DIR, exist_ok=True)
    frames[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=frames[1:],
        optimize=True,
        duration=int(1000 / FPS),
        loop=0
    )

    file_size_kb = os.path.getsize(OUTPUT_GIF) / 1024
    print(f"\n==================== GENERATION COMPLETE ====================")
    print(f"Output File: {OUTPUT_GIF}")
    print(f"Total Frames: {len(frames)} | Frame Rate: {FPS} FPS")
    print(f"Total Duration: {len(frames) / FPS:.2f} seconds")
    print(f"File Size: {file_size_kb:.1f} KB ({file_size_kb / 1024:.2f} MB)")
    print(f"Final Coins: {total_coins} / {total_coins}")
    print(f"=============================================================\n")

if __name__ == "__main__":
    main()
