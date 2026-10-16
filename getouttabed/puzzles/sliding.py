from gi.repository import Gdk, Gtk

from .base import BOARD_PX, PhotoBoard, Puzzle, outline
from .logic import SlidingLogic

KEYS = {Gdk.KEY_Up: "up", Gdk.KEY_Down: "down", Gdk.KEY_Left: "left", Gdk.KEY_Right: "right"}


class Sliding(Puzzle):
    title = "Sliding Tile"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.board = PhotoBoard(ctx.photo)
        row = Gtk.Box(spacing=24)
        self.area = Gtk.DrawingArea(content_width=BOARD_PX, content_height=BOARD_PX, focusable=True)
        self.area.set_draw_func(self._draw)
        click = Gtk.GestureClick()
        click.connect("pressed", self._clicked)
        self.area.add_controller(click)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key)
        self.area.add_controller(keys)
        row.append(self.area)

        goal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.CENTER)
        thumb = Gtk.Picture(can_shrink=True, opacity=0.5)
        thumb.set_paintable(Gdk.Texture.new_for_pixbuf(ctx.photo))
        thumb.set_size_request(150, 150)
        goal.append(thumb)
        lbl = Gtk.Label(label="Goal")
        lbl.add_css_class("puzzle-feedback")
        goal.append(lbl)
        row.append(goal)
        self.append(row)
        hint = Gtk.Label(label="Click a tile next to the gap to slide it. Arrow keys work too.")
        hint.add_css_class("puzzle-feedback")
        self.append(hint)
        self.reset()

    def start(self):
        self.area.grab_focus()

    def reset(self):
        super().reset()
        self.logic = SlidingLogic()
        self._refresh()

    def _refresh(self):
        placed = sum(1 for i, t in enumerate(self.logic.board) if i == t and t != self.logic.gap_tile)
        self.progress.set_label(f"Tiles in place: {placed} / 8")
        self.area.queue_draw()
        if self.logic.solved:
            self.finish(900)

    def _clicked(self, _g, _n, x, y):
        self.area.grab_focus()
        if self.logic.solved:
            return
        pos = self.board.cell_at(self.area.get_width(), self.area.get_height(), x, y)
        if pos is not None and self.logic.move(pos):
            self._refresh()

    def _key(self, _c, keyval, _code, _state):
        d = KEYS.get(keyval)
        if d is None:
            return False
        if not self.logic.solved and self.logic.move_direction(d):
            self._refresh()
        return True

    def _draw(self, _area, cr, w, h):
        ox, oy, t = self.board.geometry(w, h)
        solved = self.logic.solved
        for pos, tile in enumerate(self.logic.board):
            r, c = divmod(pos, 3)
            x, y = ox + c * t, oy + r * t
            if tile == self.logic.gap_tile and not solved:
                cr.set_source_rgb(0.05, 0.1, 0.2)
                cr.rectangle(x, y, t, t)
                cr.fill()
                continue
            self.board.draw_tile(cr, tile, x, y, t)
            if not solved:
                outline(cr, x, y, t, (1, 1, 1), 2)
