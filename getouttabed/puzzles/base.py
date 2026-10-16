from gi.repository import GLib, GObject, Gtk


class PuzzleContext:
    """What a puzzle may use: the photo, sound effects, and duck(True/False) to silence the messages."""

    def __init__(self, photo, effects, duck):
        self.photo = photo
        self.effects = effects
        self.duck = duck


class Puzzle(Gtk.Box):
    """Common interface: start(), reset(), and a 'solved' signal (emitted once)."""

    __gsignals__ = {"solved": (GObject.SignalFlags.RUN_FIRST, None, ())}
    title = ""

    def __init__(self, ctx: PuzzleContext):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14, halign=Gtk.Align.CENTER,
                         valign=Gtk.Align.CENTER, vexpand=True, hexpand=True)
        self.ctx = ctx
        self._done = False
        heading = Gtk.Label(label=self.title)
        heading.add_css_class("puzzle-title")
        self.append(heading)
        self.progress = Gtk.Label()
        self.progress.add_css_class("puzzle-progress")
        self.append(self.progress)

    def start(self) -> None:
        pass

    def reset(self) -> None:
        self._done = False

    def finish(self, delay_ms: int = 500) -> None:
        if self._done:
            return
        self._done = True
        GLib.timeout_add(delay_ms, lambda: self.emit("solved") and False)


BOARD_PX = 480


class PhotoBoard:
    """Helpers for drawing an n×n grid of photo tiles in a square DrawingArea."""

    def __init__(self, photo, n: int = 3):
        self.photo, self.n = photo, n
        self._scaled = None

    def geometry(self, w: int, h: int):
        side = min(w, h)
        return (w - side) / 2, (h - side) / 2, side / self.n

    def scaled(self, side: int):
        from gi.repository import GdkPixbuf
        side = max(1, int(side))
        if self._scaled is None or self._scaled.get_width() != side:
            self._scaled = self.photo.scale_simple(side, side, GdkPixbuf.InterpType.BILINEAR)
        return self._scaled

    def draw_tile(self, cr, tile: int, x: float, y: float, t: float, alpha: float = 1.0):
        from gi.repository import Gdk
        sr, sc = divmod(tile, self.n)
        img = self.scaled(t * self.n)
        cr.save()
        cr.rectangle(x, y, t, t)
        cr.clip()
        Gdk.cairo_set_source_pixbuf(cr, img, x - sc * t, y - sr * t)
        cr.paint_with_alpha(alpha)
        cr.restore()

    def cell_at(self, w, h, px, py):
        ox, oy, t = self.geometry(w, h)
        c, r = int((px - ox) // t), int((py - oy) // t)
        if 0 <= c < self.n and 0 <= r < self.n:
            return r * self.n + c
        return None


def outline(cr, x, y, t, rgb, width):
    cr.set_source_rgb(*rgb)
    cr.set_line_width(width)
    cr.rectangle(x + width / 2, y + width / 2, t - width, t - width)
    cr.stroke()


def checkmark(cr, x, y, size):
    cr.set_source_rgba(0.1, 0.65, 0.3, 0.9)
    cr.arc(x + size / 2, y + size / 2, size / 2, 0, 6.2832)
    cr.fill()
    cr.set_source_rgb(1, 1, 1)
    cr.set_line_width(size / 7)
    cr.move_to(x + size * 0.27, y + size * 0.52)
    cr.line_to(x + size * 0.44, y + size * 0.68)
    cr.line_to(x + size * 0.74, y + size * 0.34)
    cr.stroke()
