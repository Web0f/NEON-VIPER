"""
Запуск:     python snake.py

Управление:
  Стрелки / WASD — движение
  P или ESC      — пауза
  Enter          — старт / рестарт
  F11            — вкл/выкл полноэкранный режим
  В меню: ↑↓ выбор, ←→ изменение, Enter — начать
"""

import pygame
import random
import math
import json
import os
import sys
import array

# ─────────────────────────── ИНИЦИАЛИЗАЦИЯ ───────────────────────────
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

CELL = 25
COLS, ROWS = 32, 22
HUD_H = 80
W, PLAY_H = COLS * CELL, ROWS * CELL
H = PLAY_H + HUD_H

# ─────────────────────────── ДИСПЛЕЙ ───────────────────────────
# screen — внутренний холст ФИКСИРОВАННОГО размера (W × H).
# display — реальное окно (может быть больше в фуллскрине).
# ВАЖНО: .convert() требует, чтобы окно уже было создано через set_mode().
display = None
fullscreen = False
screen = None  # создаётся ниже, после create_display(False)

def create_display(fs):
    """Создаёт/пересоздаёт окно. fs=True — фуллскрин."""
    global display, fullscreen
    fullscreen = bool(fs)
    if fullscreen:
        display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        display = pygame.display.set_mode((W, H))
    cap = "NEON VIPER  •  F11 — " + ("выход из фуллскрина" if fullscreen else "полный экран")
    pygame.display.set_caption(cap)

def present():
    """Рисует холст `screen` в окно `display` с letterbox-масштабированием."""
    dw, dh = display.get_size()
    if (dw, dh) == (W, H) and not fullscreen:
        display.blit(screen, (0, 0))
    else:
        scale = min(dw / W, dh / H)
        nw, nh = max(1, int(W * scale)), max(1, int(H * scale))
        scaled = pygame.transform.scale(screen, (nw, nh))
        ox = (dw - nw) // 2
        oy = (dh - nh) // 2
        display.fill((0, 0, 0))
        display.blit(scaled, (ox, oy))
    pygame.display.flip()

def toggle_fullscreen():
    """Переключает фуллскрин ↔ окно."""
    create_display(not fullscreen)

create_display(False)                       # сначала создаём окно
screen = pygame.Surface((W, H)).convert()   # теперь .convert() работает

clock = pygame.time.Clock()
FPS = 60

pygame.key.set_repeat(160, 70)

# ─────────────────────────── ЦВЕТА ───────────────────────────
BG_TOP      = (10, 12, 24)
BG_BOT      = (24, 12, 42)
GRID_COL    = (255, 255, 255, 9)
TEXT_COL    = (232, 238, 255)
TEXT_DIM    = (130, 145, 180)
ACCENT      = (0, 235, 175)
ACCENT2     = (255, 90, 140)
PANEL       = (16, 20, 36)

SNAKE_THEMES = [
    ("НЕОН",   (60, 255, 180),  (40, 110, 220)),
    ("ЛАВА",   (255, 200, 80),  (210, 45, 60)),
    ("ЛЁД",    (190, 245, 255), (40, 100, 210)),
    ("ЯД",     (170, 255, 70),  (30, 140, 50)),
    ("РОЗА",   (255, 150, 210), (185, 30, 130)),
    ("ЗОЛОТО", (255, 235, 120), (205, 135, 25)),
    ("ФИОЛЕТ", (205, 140, 255), (95, 40, 205)),
    ("МОНО",   (230, 230, 235), (95, 100, 115)),
]

FOOD_CFG = {
    "apple":  dict(score=10, grow=1,  color=(255, 70, 95)),
    "golden": dict(score=50, grow=3,  color=(255, 205, 60)),
    "slow":   dict(score=15, grow=1,  color=(90, 190, 255)),
    "shrink": dict(score=25, grow=-3, color=(195, 110, 255)),
}

DIFFS = ["ЛЕГКО", "НОРМА", "СЛОЖНО", "ХАРДКОР"]
DIFF_CFG = {
    "ЛЕГКО":   dict(base=0.150, mn=0.085, accel=0.0035, mult=1),
    "НОРМА":   dict(base=0.120, mn=0.065, accel=0.0045, mult=2),
    "СЛОЖНО":  dict(base=0.095, mn=0.050, accel=0.0055, mult=3),
    "ХАРДКОР": dict(base=0.070, mn=0.038, accel=0.0070, mult=5),
}

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "neon_viper.json")

# ─────────────────────────── ШРИФТЫ ───────────────────────────
FONT_NAMES = "arial,dejavusans,liberationsans,freesans,verdana,tahoma,segoeui,consolas"

def F(size, bold=False):
    try:
        return pygame.font.SysFont(FONT_NAMES, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)

f_title = F(66, True)
f_big   = F(44, True)
f_med   = F(26, True)
f_small = F(19)
f_tiny  = F(16)

# ─────────────────────────── ЗВУКИ ───────────────────────────
SOUNDS = {}

def init_sounds():
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    except Exception:
        return

    def tone(freq, ms, vol=0.25, sweep=0.0, wave="sine"):
        sr = 44100
        n = max(1, int(sr * ms / 1000.0))
        buf = array.array('h')
        phase = 0.0
        for i in range(n):
            f = freq + sweep * (i / n)
            phase += 2.0 * math.pi * f / sr
            if wave == "sine":
                v = math.sin(phase)
            elif wave == "square":
                v = 1.0 if math.sin(phase) >= 0 else -1.0
            else:
                v = 2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0
            env = min(1.0, i / (sr * 0.004)) * min(1.0, (n - i) / (sr * 0.03))
            buf.append(int(max(-1.0, min(1.0, v)) * env * vol * 32767))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    try:
        SOUNDS['eat']   = tone(600, 80,  0.30, sweep=350)
        SOUNDS['gold']  = tone(880, 190, 0.30, sweep=650)
        SOUNDS['power'] = tone(520, 170, 0.26, sweep=-200, wave="saw")
        SOUNDS['die']   = tone(320, 520, 0.35, sweep=-240, wave="saw")
        SOUNDS['turn']  = tone(1300, 22, 0.05)
        SOUNDS['click'] = tone(760, 45,  0.16)
        SOUNDS['level'] = tone(600, 240, 0.26, sweep=520)
    except Exception:
        SOUNDS.clear()

init_sounds()

def play(name):
    s = SOUNDS.get(name)
    if s:
        try:
            s.play()
        except Exception:
            pass

# ─────────────────────────── УТИЛИТЫ ───────────────────────────
def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))

def scale_color(c, k):
    return (max(0, min(255, int(c[0] * k))),
            max(0, min(255, int(c[1] * k))),
            max(0, min(255, int(c[2] * k))))

def load_data():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("highscores", {})
        d.setdefault("wrap", False)
        d.setdefault("diff", 1)
        d.setdefault("color", 0)
        d.setdefault("fullscreen", False)
        return d
    except Exception:
        return {"highscores": {}, "wrap": False, "diff": 1, "color": 0, "fullscreen": False}

def save_data(d):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def draw_text(surf, text, font, color, pos, center=False, shadow=True):
    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        r = sh.get_rect(center=pos) if center else sh.get_rect(topleft=pos)
        surf.blit(sh, (r.x + 2, r.y + 2))
    img = font.render(text, True, color)
    r = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, r)
    return r

def glow_text(surf, text, font, color, pos, center=True, strength=3):
    img = font.render(text, True, color)
    r = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    g = pygame.Surface((r.width + 40, r.height + 40), pygame.SRCALPHA)
    for radius in range(strength, 0, -1):
        a = int(46 / radius)
        tmp = font.render(text, True, (*color, a))
        tmp.set_alpha(a)
        g.blit(tmp, (20, 20))
        g.blit(tmp, (20 - radius, 20))
        g.blit(tmp, (20 + radius, 20))
        g.blit(tmp, (20, 20 - radius))
        g.blit(tmp, (20, 20 + radius))
    surf.blit(g, (r.x - 20, r.y - 20))
    surf.blit(img, r)
    return r

# ─────────────────────────── ФОН ───────────────────────────
def make_play_bg():
    s = pygame.Surface((W, PLAY_H))
    for y in range(PLAY_H):
        t = y / max(1, PLAY_H - 1)
        c = (int(lerp(BG_TOP[0], BG_BOT[0], t)),
             int(lerp(BG_TOP[1], BG_BOT[1], t)),
             int(lerp(BG_TOP[2], BG_BOT[2], t)))
        pygame.draw.line(s, c, (0, y), (W, y))
    g = pygame.Surface((W, PLAY_H), pygame.SRCALPHA)
    for x in range(0, W + 1, CELL):
        pygame.draw.line(g, GRID_COL, (x, 0), (x, PLAY_H))
    for y in range(0, PLAY_H + 1, CELL):
        pygame.draw.line(g, GRID_COL, (0, y), (W, y))
    s.blit(g, (0, 0))
    return s

PLAY_BG = make_play_bg()

# ─────────────────────────── ИГРА ───────────────────────────
class Viper:
    def __init__(self):
        self.data = load_data()
        self.diff_index = int(self.data.get("diff", 1)) % len(DIFFS)
        self.wrap = bool(self.data.get("wrap", False))
        self.color_index = int(self.data.get("color", 0)) % len(SNAKE_THEMES)
        self.state = "menu"
        self.menu_index = 0
        self.menu_items = 4
        self.t = 0.0
        self.new_record = False
        self.reset()

    # ---------- цвета змейки ----------
    def theme(self):
        return SNAKE_THEMES[self.color_index]

    def head_color(self):
        return self.theme()[1]

    def tail_color(self):
        return self.theme()[2]

    # ---------- сброс ----------
    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.prev_snake = list(self.snake)
        self.direction = (1, 0)
        self.input_queue = []
        self.grow = 0
        self.score = 0
        self.apples = 0
        self.level = 1
        self.step_timer = 0.0
        self.foods = []
        self.particles = []
        self.popups = []
        self.shake = 0.0
        self.slow_timer = 0.0
        self.special_timer = random.uniform(6.0, 10.0)
        self.flash = 0.0
        self.over_timer = 0.0
        self.new_record = False
        self.spawn_apple()

    # ---------- параметры ----------
    def interval(self):
        cfg = DIFF_CFG[DIFFS[self.diff_index]]
        base = max(cfg["mn"], cfg["base"] - (self.level - 1) * cfg["accel"])
        if self.slow_timer > 0:
            base *= 1.7
        return base

    def mult(self):
        return DIFF_CFG[DIFFS[self.diff_index]]["mult"]

    # ---------- еда ----------
    def free_cells(self):
        occ = set(self.snake) | {f["pos"] for f in self.foods}
        return [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in occ]

    def spawn_apple(self):
        cells = self.free_cells()
        if cells:
            self.foods.append({"pos": random.choice(cells), "kind": "apple",
                               "ttl": None, "age": 0.0})

    def spawn_special(self):
        if any(f["kind"] != "apple" for f in self.foods):
            return
        cells = self.free_cells()
        if not cells:
            return
        r = random.random()
        if r < 0.50:
            kind = "golden"
        elif r < 0.80:
            kind = "slow"
        else:
            kind = "shrink"
        ttl = {"golden": 7.0, "slow": 9.0, "shrink": 9.0}[kind]
        self.foods.append({"pos": random.choice(cells), "kind": kind,
                           "ttl": ttl, "age": 0.0})

    # ---------- ввод ----------
    def push_input(self, d):
        last = self.input_queue[-1] if self.input_queue else self.direction
        if d == last:
            return
        if d[0] == -last[0] and d[1] == -last[1]:
            return
        if len(self.input_queue) < 2:
            self.input_queue.append(d)
            play('turn')

    def cycle_color(self, step):
        self.color_index = (self.color_index + step) % len(SNAKE_THEMES)
        self.data["color"] = self.color_index
        save_data(self.data)
        play('click')

    def set_fullscreen(self, value):
        create_display(value)
        self.data["fullscreen"] = bool(value)
        save_data(self.data)

    def handle_key(self, key):
        # F11 работает ВЕЗДЕ и всегда
        if key == pygame.K_F11:
            self.set_fullscreen(not fullscreen)
            play('click')
            return

        if self.state == "menu":
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % self.menu_items
                play('click')
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % self.menu_items
                play('click')
            elif key in (pygame.K_LEFT, pygame.K_a):
                if self.menu_index == 0:
                    self.diff_index = (self.diff_index - 1) % len(DIFFS)
                    self.data["diff"] = self.diff_index
                    save_data(self.data)
                    play('click')
                elif self.menu_index == 1:
                    self.wrap = not self.wrap
                    self.data["wrap"] = self.wrap
                    save_data(self.data)
                    play('click')
                elif self.menu_index == 2:
                    self.cycle_color(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                if self.menu_index == 0:
                    self.diff_index = (self.diff_index + 1) % len(DIFFS)
                    self.data["diff"] = self.diff_index
                    save_data(self.data)
                    play('click')
                elif self.menu_index == 1:
                    self.wrap = not self.wrap
                    self.data["wrap"] = self.wrap
                    save_data(self.data)
                    play('click')
                elif self.menu_index == 2:
                    self.cycle_color(1)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if self.menu_index == 3:
                    self.start_game()
                else:
                    self.menu_index = 3
                    play('click')

        elif self.state == "play":
            if key in (pygame.K_UP, pygame.K_w):
                self.push_input((0, -1))
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.push_input((0, 1))
            elif key in (pygame.K_LEFT, pygame.K_a):
                self.push_input((-1, 0))
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.push_input((1, 0))
            elif key in (pygame.K_ESCAPE, pygame.K_p):
                self.state = "pause"
                play('click')

        elif self.state == "pause":
            if key in (pygame.K_ESCAPE, pygame.K_p, pygame.K_RETURN, pygame.K_SPACE):
                self.state = "play"
                play('click')
            elif key == pygame.K_m:
                self.state = "menu"
                play('click')

        elif self.state == "over":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.start_game()
            elif key == pygame.K_ESCAPE:
                self.state = "menu"
                play('click')

    def start_game(self):
        self.reset()
        self.state = "play"
        play('click')

    # ---------- смерть ----------
    def die(self):
        self.state = "over"
        self.over_timer = 0.0
        self.shake = 16.0
        self.flash = 1.0
        play('die')

        hx, hy = self.snake[0]
        px = hx * CELL + CELL / 2
        py = hy * CELL + CELL / 2
        for _ in range(70):
            a = random.uniform(0, math.tau)
            sp = random.uniform(40, 340)
            self.particles.append({
                "x": px, "y": py,
                "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                "life": random.uniform(0.4, 1.1), "max_life": 1.1,
                "color": random.choice([self.head_color(), self.tail_color(), (255, 90, 120)]),
                "size": random.uniform(2, 5)
            })

        key = DIFFS[self.diff_index]
        best = self.data["highscores"].get(key, 0)
        if self.score > best:
            self.new_record = True
            self.data["highscores"][key] = self.score
            save_data(self.data)

    # ---------- шаг змейки ----------
    def step_snake(self):
        if self.input_queue:
            self.direction = self.input_queue.pop(0)

        self.prev_snake = list(self.snake)
        hx, hy = self.snake[0]
        dx, dy = self.direction
        nx, ny = hx + dx, hy + dy

        if self.wrap:
            nx %= COLS
            ny %= ROWS
        elif not (0 <= nx < COLS and 0 <= ny < ROWS):
            self.die()
            return

        occupied = self.snake if self.grow > 0 else self.snake[:-1]
        if (nx, ny) in occupied:
            self.die()
            return

        self.snake.insert(0, (nx, ny))
        if self.grow > 0:
            self.grow -= 1
        else:
            self.snake.pop()

        for f in list(self.foods):
            if f["pos"] == (nx, ny):
                self.foods.remove(f)
                self.apply_food(f)
                break

    def apply_food(self, f):
        cfg = FOOD_CFG[f["kind"]]
        pts = cfg["score"] * self.mult()
        self.score += pts
        self.grow += max(0, cfg["grow"])

        if cfg["grow"] < 0:
            for _ in range(-cfg["grow"]):
                if len(self.snake) > 4:
                    self.snake.pop()
            self.prev_snake = list(self.snake)

        if f["kind"] == "slow":
            self.slow_timer = 5.0
            play('power')
        elif f["kind"] == "golden":
            play('gold')
            self.shake = max(self.shake, 6.0)
            self.flash = max(self.flash, 0.5)
        else:
            play('eat')

        fx = f["pos"][0] * CELL + CELL / 2
        fy = f["pos"][1] * CELL + CELL / 2
        n = 26 if f["kind"] == "golden" else 14
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(30, 200)
            self.particles.append({
                "x": fx, "y": fy,
                "vx": math.cos(a) * sp, "vy": math.sin(a) * sp,
                "life": random.uniform(0.3, 0.8), "max_life": 0.8,
                "color": cfg["color"], "size": random.uniform(2, 4)
            })

        self.popups.append({
            "x": fx, "y": fy, "text": f"+{pts}",
            "color": cfg["color"], "life": 0.9, "max_life": 0.9
        })

        if f["kind"] == "apple":
            self.apples += 1
            new_lvl = self.apples // 5 + 1
            if new_lvl > self.level:
                self.level = new_lvl
                play('level')
                self.popups.append({
                    "x": W / 2, "y": PLAY_H / 2, "text": f"УРОВЕНЬ {self.level}",
                    "color": self.head_color(), "life": 1.4, "max_life": 1.4, "big": True
                })
            self.spawn_apple()

    # ---------- обновление ----------
    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt * 2.2)
        self.shake = max(0.0, self.shake - dt * 42.0)

        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.965
            p["vy"] *= 0.965
            p["vy"] += 90 * dt
            p["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0]

        for p in self.popups:
            p["y"] -= 34 * dt
            p["life"] -= dt
        self.popups = [p for p in self.popups if p["life"] > 0]

        if self.state == "over":
            self.over_timer += dt

        if self.state != "play":
            return

        if self.slow_timer > 0:
            self.slow_timer = max(0.0, self.slow_timer - dt)

        for f in self.foods:
            f["age"] += dt
            if f["ttl"] is not None:
                f["ttl"] -= dt
        self.foods = [f for f in self.foods
                      if f["ttl"] is None or f["ttl"] > 0]

        if not any(f["kind"] == "apple" for f in self.foods):
            self.spawn_apple()

        self.special_timer -= dt
        if self.special_timer <= 0:
            self.spawn_special()
            self.special_timer = random.uniform(7.0, 12.0)

        self.step_timer += dt
        guard = 0
        while self.state == "play" and self.step_timer >= self.interval() and guard < 5:
            guard += 1
            self.step_timer -= self.interval()
            self.step_snake()

    # ---------- точки змейки ----------
    def snake_points(self, t):
        body = self.snake
        prev = self.prev_snake
        if len(body) == len(prev) + 1:
            prev = [prev[0]] + prev
        elif len(body) != len(prev):
            prev = list(body)

        pts = []
        for i, (bx, by) in enumerate(body):
            px, py = prev[i] if i < len(prev) else prev[-1]
            if abs(bx - px) > 1 or abs(by - py) > 1:
                px, py = bx, by
            x = lerp(px, bx, t) * CELL + CELL / 2
            y = lerp(py, by, t) * CELL + CELL / 2
            pts.append((x, y))
        return pts

    # ---------- отрисовка игровой зоны ----------
    def draw_play(self, surf):
        surf.blit(PLAY_BG, (0, 0))

        glow = pygame.Surface((W, PLAY_H))
        glow.fill((0, 0, 0))

        pulse = 0.5 + 0.5 * math.sin(self.t * 2.0)
        border_col = lerp_color(scale_color(self.head_color(), 0.4),
                                self.head_color(), pulse)
        pygame.draw.rect(surf, border_col, (0, 0, W, PLAY_H), 3, border_radius=4)

        for f in self.foods:
            cfg = FOOD_CFG[f["kind"]]
            base_col = cfg["color"]
            cx = f["pos"][0] * CELL + CELL / 2
            cy = f["pos"][1] * CELL + CELL / 2

            blink = 1.0
            if f["ttl"] is not None and f["ttl"] < 2.0:
                blink = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(self.t * 16))
            scale = 1.0 + 0.10 * math.sin(self.t * 5.0 + f["pos"][0])

            r = CELL * 0.34 * scale
            col = scale_color(base_col, blink)

            pygame.draw.circle(glow, scale_color(base_col, 0.30 * blink),
                               (int(cx), int(cy)), int(r * 2.4))
            pygame.draw.circle(surf, (0, 0, 0), (int(cx + 2), int(cy + 3)), int(r))
            pygame.draw.circle(surf, col, (int(cx), int(cy)), int(r))
            pygame.draw.circle(surf, scale_color(col, 1.55),
                               (int(cx - r * 0.3), int(cy - r * 0.35)), max(1, int(r * 0.32)))

            if f["ttl"] is not None:
                frac = max(0.0, f["ttl"] / {"golden": 7.0, "slow": 9.0, "shrink": 9.0}[f["kind"]])
                if frac < 1.0:
                    pygame.draw.arc(surf, scale_color(base_col, 1.3),
                                    (cx - r - 5, cy - r - 5, (r + 5) * 2, (r + 5) * 2),
                                    -math.pi / 2, -math.pi / 2 + math.tau * frac, 3)

        pts = self.snake_points(min(1.0, self.step_timer / max(0.001, self.interval())))
        self.draw_snake(surf, glow, pts)

        for p in self.particles:
            k = max(0.0, p["life"] / p["max_life"])
            c = scale_color(p["color"], k)
            pygame.draw.circle(surf, c, (int(p["x"]), int(p["y"])),
                               max(1, int(p["size"] * k)))
            pygame.draw.circle(glow, scale_color(p["color"], 0.35 * k),
                               (int(p["x"]), int(p["y"])), max(1, int(p["size"] * 2.2 * k)))

        surf.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        for p in self.popups:
            k = max(0.0, p["life"] / p["max_life"])
            font = f_med if p.get("big") else f_small
            col = scale_color(p["color"], 0.25 + 0.75 * k)
            img = font.render(p["text"], True, col)
            r = img.get_rect(center=(p["x"], p["y"]))
            surf.blit(img, r)

        if self.flash > 0.01:
            fl = pygame.Surface((W, PLAY_H))
            fl.fill((255, 255, 255))
            fl.set_alpha(int(70 * self.flash))
            surf.blit(fl, (0, 0))

    def draw_snake(self, surf, glow, pts):
        n = len(pts)
        if n == 0:
            return
        base_r = CELL * 0.46
        head_col = self.head_color()
        tail_col = self.tail_color()

        for i in range(n - 1, -1, -1):
            x, y = pts[i]
            f = i / max(1, n - 1)
            r = base_r * (0.70 + 0.30 * (1.0 - f))
            col = lerp_color(head_col, tail_col, f)

            if i > 0:
                x2, y2 = pts[i - 1]
                pygame.draw.line(surf, col, (int(x), int(y)), (int(x2), int(y2)),
                                 max(2, int(r * 2)))
                pygame.draw.line(glow, scale_color(col, 0.28),
                                 (int(x), int(y)), (int(x2), int(y2)),
                                 max(3, int(r * 2) + 9))
            pygame.draw.circle(surf, col, (int(x), int(y)), max(1, int(r)))
            pygame.draw.circle(glow, scale_color(col, 0.28),
                               (int(x), int(y)), max(1, int(r) + 5))

        hx, hy = pts[0]
        hr = base_r * 1.10
        pygame.draw.circle(surf, scale_color(head_col, 1.10), (int(hx), int(hy)), int(hr))
        pygame.draw.circle(glow, scale_color(head_col, 0.40), (int(hx), int(hy)), int(hr) + 7)

        dx, dy = self.direction
        px, py = -dy, dx
        er = CELL * 0.135
        for s in (-1, 1):
            ex = hx + dx * CELL * 0.19 + px * s * CELL * 0.17
            ey = hy + dy * CELL * 0.19 + py * s * CELL * 0.17
            pygame.draw.circle(surf, (255, 255, 255), (int(ex), int(ey)), max(2, int(er) + 1))
            pygame.draw.circle(surf, (8, 10, 22),
                               (int(ex + dx * 2.2), int(ey + dy * 2.2)),
                               max(1, int(er * 0.62)))

    # ---------- HUD ----------
    def draw_hud(self):
        pygame.draw.rect(screen, PANEL, (0, 0, W, HUD_H))
        pygame.draw.line(screen, scale_color(self.head_color(), 0.6),
                         (0, HUD_H - 2), (W, HUD_H - 2), 2)

        diff = DIFFS[self.diff_index]
        best = self.data["highscores"].get(diff, 0)

        draw_text(screen, "СЧЁТ", f_tiny, TEXT_DIM, (24, 12))
        draw_text(screen, str(self.score), f_med, TEXT_COL, (24, 30))

        draw_text(screen, "РЕКОРД", f_tiny, TEXT_DIM, (210, 12))
        draw_text(screen, str(max(best, self.score)), f_med,
                  (255, 205, 60) if self.score >= best and self.score > 0 else TEXT_COL,
                  (210, 30))

        draw_text(screen, "УРОВЕНЬ", f_tiny, TEXT_DIM, (400, 12))
        draw_text(screen, str(self.level), f_med, self.head_color(), (400, 30))

        draw_text(screen, "ДЛИНА", f_tiny, TEXT_DIM, (540, 12))
        draw_text(screen, str(len(self.snake)), f_med, TEXT_COL, (540, 30))

        pygame.draw.circle(screen, self.head_color(), (680, 22), 9)
        pygame.draw.circle(screen, self.tail_color(), (680, 42), 9)
        name = self.theme()[0]
        img = f_tiny.render(name, True, TEXT_DIM)
        screen.blit(img, (695, 14))

        img = f_tiny.render(diff, True, ACCENT2)
        screen.blit(img, (W - 24 - img.get_width(), 12))
        mode = "СКВОЗЬ СТЕНЫ" if self.wrap else "СТЕНЫ СМЕРТЕЛЬНЫ"
        img2 = f_tiny.render(mode, True, TEXT_DIM)
        screen.blit(img2, (W - 24 - img2.get_width(), 36))

        if self.slow_timer > 0:
            bar_w = int(120 * (self.slow_timer / 5.0))
            pygame.draw.rect(screen, (30, 60, 100), (24, 62, 120, 6), border_radius=3)
            pygame.draw.rect(screen, (90, 190, 255), (24, 62, bar_w, 6), border_radius=3)

    # ---------- меню ----------
    def draw_color_preview(self, cx, cy):
        head_col = self.head_color()
        tail_col = self.tail_color()
        n = 7
        seg = 16
        for i in range(n):
            f = i / (n - 1)
            col = lerp_color(head_col, tail_col, f)
            r = 10 - int(f * 3)
            x = cx - i * seg + 40
            y = cy + int(math.sin(i * 0.9 + self.t * 3) * 3)
            pygame.draw.circle(screen, scale_color(col, 0.3),
                               (int(x), int(y)), r + 3)
            pygame.draw.circle(screen, col, (int(x), int(y)), r)
        hx = cx + 40
        pygame.draw.circle(screen, (255, 255, 255), (hx + 3, cy - 3), 3)
        pygame.draw.circle(screen, (255, 255, 255), (hx + 3, cy + 3), 3)
        pygame.draw.circle(screen, (8, 10, 22), (hx + 5, cy - 3), 2)
        pygame.draw.circle(screen, (8, 10, 22), (hx + 5, cy + 3), 2)

    def draw_menu(self):
        screen.blit(PLAY_BG, (0, 0))
        t = self.t

        for i in range(60):
            x = (i * 137 + t * 40) % (W + 40) - 20
            y = (i * 89 + math.sin(t * 1.5 + i) * 40) % PLAY_H
            a = 0.10 + 0.10 * math.sin(t * 3 + i)
            pygame.draw.circle(screen, (int(60 * a + 20), int(200 * a), int(180 * a)),
                               (int(x), int(y)), 2)

        glow_text(screen, "NEON VIPER", f_title, self.head_color(), (W / 2, 100))

        sub = f_small.render("питон • неон • бесконечность", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(center=(W / 2, 152)))

        items = [
            ("СЛОЖНОСТЬ", DIFFS[self.diff_index]),
            ("СТЕНЫ", "ПРОХОДИМЫ" if self.wrap else "СМЕРТЕЛЬНЫ"),
            ("ЦВЕТ ЗМЕЙКИ", self.theme()[0]),
            ("НАЧАТЬ ИГРУ", ""),
        ]

        y0 = 220
        for i, (label, val) in enumerate(items):
            sel = (i == self.menu_index)
            cy = y0 + i * 58

            if sel:
                pulse = 0.5 + 0.5 * math.sin(t * 6)
                col = lerp_color(self.head_color(), (255, 255, 255), 0.3 * pulse)
                pygame.draw.rect(screen, (18, 30, 46),
                                 (W / 2 - 250, cy - 22, 500, 46), border_radius=10)
                pygame.draw.rect(screen, col, (W / 2 - 250, cy - 22, 500, 46), 2,
                                 border_radius=10)
                txt_col = col
            else:
                txt_col = TEXT_DIM

            if val:
                draw_text(screen, label, f_med, txt_col, (W / 2 - 220, cy - 14), shadow=False)
                v = f_med.render(val, True, txt_col)
                screen.blit(v, (W / 2 + 220 - v.get_width(), cy - 14))
                if sel:
                    for ax, dxx in ((W / 2 - 235, -1), (W / 2 + 215, 1)):
                        pygame.draw.polygon(screen, txt_col, [
                            (ax, cy), (ax + 12 * dxx, cy - 9), (ax + 12 * dxx, cy + 9)])
            else:
                draw_text(screen, label, f_med, txt_col, (W / 2, cy - 14),
                          center=True, shadow=False)

        prev_y = 220 + 3 * 58 + 55
        draw_text(screen, "ПРЕВЬЮ", f_tiny, TEXT_DIM, (W / 2, prev_y - 20),
                  center=True, shadow=False)
        self.draw_color_preview(W / 2, prev_y)

        rec_y = 500
        draw_text(screen, "— РЕКОРДЫ —", f_small, TEXT_DIM, (W / 2, rec_y),
                  center=True, shadow=False)
        rec_y += 26
        for d in DIFFS:
            hs = self.data["highscores"].get(d, 0)
            col = self.head_color() if d == DIFFS[self.diff_index] else TEXT_DIM
            draw_text(screen, d, f_tiny, col, (W / 2 - 150, rec_y), shadow=False)
            v = f_tiny.render(str(hs), True, col)
            screen.blit(v, (W / 2 + 150 - v.get_width(), rec_y))
            rec_y += 20

        hint = f_tiny.render("↑↓ — выбор    ←→ — изменить    ENTER — начать    F11 — фуллскрин",
                             True, TEXT_DIM)
        screen.blit(hint, hint.get_rect(center=(W / 2, H - 20)))

    # ---------- оверлеи ----------
    def draw_overlay(self, title, lines, color, title_size=52):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 175))
        screen.blit(ov, (0, 0))
        glow_text(screen, title, F(title_size, True), color, (W / 2, H / 2 - 110))
        y = H / 2 - 30
        for txt, col, sz in lines:
            img = F(sz, bold=(sz > 24)).render(txt, True, col)
            screen.blit(img, img.get_rect(center=(W / 2, y)))
            y += sz + 20

    # ---------- общая отрисовка ----------
    def draw(self):
        screen.fill((0, 0, 0))

        if self.state == "menu":
            self.draw_menu()
            return

        play_surf = pygame.Surface((W, PLAY_H))
        self.draw_play(play_surf)

        sx = sy = 0
        if self.shake > 0.1:
            sx = int(random.uniform(-self.shake, self.shake) * 0.5)
            sy = int(random.uniform(-self.shake, self.shake) * 0.5)

        screen.blit(play_surf, (sx, HUD_H + sy))

        self.draw_hud()

        if self.state == "pause":
            self.draw_overlay("ПАУЗА", [
                ("Продолжить — P / ENTER", TEXT_COL, 24),
                ("В меню — M", TEXT_DIM, 20),
                ("F11 — фуллскрин", TEXT_DIM, 18),
            ], self.head_color())

        elif self.state == "over":
            if self.over_timer < 0.35:
                return
            diff = DIFFS[self.diff_index]
            best = self.data["highscores"].get(diff, 0)
            lines = [
                (f"СЧЁТ: {self.score}", TEXT_COL, 30),
                (f"РЕКОРД: {best}", (255, 205, 60), 26),
                (f"УРОВЕНЬ: {self.level}   ДЛИНА: {len(self.snake)}", TEXT_DIM, 22),
                ("", TEXT_COL, 10),
                ("ENTER — заново    ESC — в меню", TEXT_DIM, 20),
            ]
            if self.new_record:
                lines.insert(0, ("★ НОВЫЙ РЕКОРД ★", (255, 220, 80), 30))
            self.draw_overlay("ИГРА ОКОНЧЕНА", lines, ACCENT2, 46)


# ─────────────────────────── MAIN ───────────────────────────
def main():
    game = Viper()
    # применяем сохранённый режим экрана
    create_display(bool(game.data.get("fullscreen", False)))

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                game.handle_key(e.key)

        game.update(dt)
        game.draw()          # рисуем на холст screen
        present()            # масштабируем и выводим в окно display

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()