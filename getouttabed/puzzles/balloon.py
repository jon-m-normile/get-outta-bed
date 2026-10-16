import math
import random

from gi.repository import Gtk

from .base import Puzzle
from .logic import BalloonLogic

WIDTH, HEIGHT = 720, 520
MAX_BALLOONS = 4
SPAWN_SECONDS = 0.9
POP_SECONDS = 0.35
COLORS = [(0.95, 0.25, 0.3), (1.0, 0.6, 0.1), (0.98, 0.85, 0.2), (0.3, 0.8, 0.4),
          (0.25, 0.6, 1.0), (0.65, 0.4, 0.95), (1.0, 0.45, 0.75)]


class BalloonPop(Puzzle):
    title = "Balloon Pop"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.area = Gtk.DrawingArea(content_width=WIDTH, content_height=HEIGHT)
        self.area.set_draw_func(self._draw)
        click = Gtk.GestureClick()
        click.connect("pressed", self._clicked)
        self.area.add_controller(click)
        self.append(self.area)
        self.rng = random.Random()
        self._tick_id = None
        self.reset()

    def reset(self):
        super().reset()
        self.logic = BalloonLogic()
        self.balloons, self.pops = [], []
        self.last_spawn = -10.0
        self.t = 0.0
        self.last_frame = None
        self._update_progress()

    def start(self):
        if self._tick_id is None:
            self._tick_id = self.area.add_tick_callback(self._frame)

    def _update_progress(self):
        self.progress.set_label(f"Popped {self.logic.popped} / {BalloonLogic.TARGET}")

    def _spawn(self):
        r = self.rng.uniform(42, 56)
        w = max(self.area.get_width(), 2 * r + 2)
        self.balloons.append({
            "x": self.rng.uniform(r, w - r), "y": self.area.get_height() + r * 1.3, "r": r,
            "speed": self.rng.uniform(55, 95), "phase": self.rng.uniform(0, 6.28),
            "color": self.rng.choice(COLORS),
        })

    def _frame(self, _widget, clock):
        now = clock.get_frame_time() / 1e6
        dt = 0 if self.last_frame is None else min(now - self.last_frame, 0.1)
        self.last_frame = now
        self.t += dt
        for b in self.balloons:
            b["y"] -= b["speed"] * dt
        self.balloons = [b for b in self.balloons if b["y"] + b["r"] * 2.5 > 0]
        self.pops = [p for p in self.pops if self.t - p["t"] < POP_SECONDS]
        if not self.logic.solved and len(self.balloons) < MAX_BALLOONS and self.t - self.last_spawn > SPAWN_SECONDS:
            self._spawn()
            self.last_spawn = self.t
        self.area.queue_draw()
        return True

    def _clicked(self, _g, _n, x, y):
        for b in reversed(self.balloons):
            bx = b["x"] + 8 * math.sin(self.t * 1.5 + b["phase"])
            if ((x - bx) / b["r"]) ** 2 + ((y - b["y"]) / (b["r"] * 1.2)) ** 2 <= 1.15:
                self.balloons.remove(b)
                self.pops.append({"x": bx, "y": b["y"], "r": b["r"], "color": b["color"], "t": self.t})
                self.ctx.effects.play("pop.wav")
                if self.logic.pop():
                    self.balloons.clear()
                    self.finish(600)
                self._update_progress()
                return

    def _draw(self, _area, cr, w, h):
        sky_top, sky_bottom = (0.45, 0.7, 0.98), (0.8, 0.92, 1.0)
        import cairo
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, *sky_top)
        g.add_color_stop_rgb(1, *sky_bottom)
        cr.set_source(g)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        for b in self.balloons:
            x = b["x"] + 8 * math.sin(self.t * 1.5 + b["phase"])
            self._balloon(cr, x, b["y"], b["r"], b["color"])
        for p in self.pops:
            k = (self.t - p["t"]) / POP_SECONDS
            cr.set_source_rgba(*p["color"], 1 - k)
            cr.set_line_width(5)
            for i in range(10):
                a = i * math.pi / 5
                r0, r1 = p["r"] * (0.4 + k), p["r"] * (0.8 + 1.2 * k)
                cr.move_to(p["x"] + r0 * math.cos(a), p["y"] + r0 * math.sin(a))
                cr.line_to(p["x"] + r1 * math.cos(a), p["y"] + r1 * math.sin(a))
            cr.stroke()
        if self.logic.solved:
            cr.set_source_rgb(1, 1, 1)
            cr.select_font_face("Sans", 0, 1)
            cr.set_font_size(54)
            ext = cr.text_extents("All popped!")
            cr.move_to((w - ext.width) / 2, h / 2)
            cr.show_text("All popped!")

    @staticmethod
    def _balloon(cr, x, y, r, color):
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.7)
        cr.set_line_width(2)
        cr.move_to(x, y + r * 1.25)
        cr.curve_to(x - 10, y + r * 1.7, x + 10, y + r * 2.0, x, y + r * 2.4)
        cr.stroke()
        cr.set_source_rgb(*[c * 0.8 for c in color])
        cr.move_to(x, y + r * 1.15)
        cr.line_to(x - 7, y + r * 1.32)
        cr.line_to(x + 7, y + r * 1.32)
        cr.close_path()
        cr.fill()
        cr.save()
        cr.translate(x, y)
        cr.scale(1, 1.2)
        cr.arc(0, 0, r, 0, 2 * math.pi)
        cr.restore()
        cr.set_source_rgb(*color)
        cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.45)
        cr.save()
        cr.translate(x - r * 0.35, y - r * 0.45)
        cr.scale(1, 1.5)
        cr.arc(0, 0, r * 0.18, 0, 2 * math.pi)
        cr.restore()
        cr.fill()
