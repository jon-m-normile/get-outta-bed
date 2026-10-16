from gi.repository import Gtk

from .base import BOARD_PX, PhotoBoard, Puzzle, checkmark, outline
from .logic import JigsawLogic

DRAG_THRESHOLD = 12


class Jigsaw(Puzzle):
    title = "Picture Jigsaw"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.board = PhotoBoard(ctx.photo)
        self.area = Gtk.DrawingArea(content_width=BOARD_PX, content_height=BOARD_PX)
        self.area.set_draw_func(self._draw)
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._begin)
        drag.connect("drag-update", self._update)
        drag.connect("drag-end", self._end)
        self.area.add_controller(drag)
        self.append(self.area)
        hint = Gtk.Label(label="Click two tiles to swap them, or drag a tile onto another.")
        hint.add_css_class("puzzle-feedback")
        self.append(hint)
        self.reset()

    def reset(self):
        super().reset()
        self.logic = JigsawLogic()
        self.selected = None
        self.drag = None
        self._refresh()

    def _refresh(self):
        self.progress.set_label(f"Tiles in place: {9 - self.logic.misplaced()} / 9")
        self.area.queue_draw()

    def _cell(self, x, y):
        return self.board.cell_at(self.area.get_width(), self.area.get_height(), x, y)

    def _begin(self, _g, x, y):
        pos = self._cell(x, y)
        self.drag = {"from": pos, "x0": x, "y0": y, "dx": 0, "dy": 0, "moved": False} if pos is not None else None

    def _update(self, _g, dx, dy):
        if self.drag:
            self.drag.update(dx=dx, dy=dy)
            if abs(dx) + abs(dy) > DRAG_THRESHOLD:
                self.drag["moved"] = True
            self.area.queue_draw()

    def _end(self, _g, dx, dy):
        d, self.drag = self.drag, None
        if d is None or self.logic.solved:
            self.area.queue_draw()
            return
        if d["moved"]:
            target = self._cell(d["x0"] + dx, d["y0"] + dy)
            if target is not None and target != d["from"]:
                self.logic.swap(d["from"], target)
            self.selected = None
        else:
            pos = d["from"]
            if self.selected is None:
                self.selected = pos
            elif self.selected == pos:
                self.selected = None
            else:
                self.logic.swap(self.selected, pos)
                self.selected = None
        self._refresh()
        if self.logic.solved:
            self.finish(700)

    def _draw(self, _area, cr, w, h):
        ox, oy, t = self.board.geometry(w, h)
        dragging = self.drag and self.drag["moved"]
        for pos, tile in enumerate(self.logic.board):
            r, c = divmod(pos, 3)
            x, y = ox + c * t, oy + r * t
            ghost = dragging and pos == self.drag["from"]
            self.board.draw_tile(cr, tile, x, y, t, 0.3 if ghost else 1.0)
            if self.logic.solved:
                continue
            outline(cr, x, y, t, (1, 1, 1), 2)
            if self.logic.correct(pos):
                outline(cr, x, y, t, (0.2, 0.8, 0.4), 4)
                checkmark(cr, x + t - 34, y + 8, 26)
            if pos == self.selected:
                outline(cr, x, y, t, (1, 0.82, 0.2), 8)
        if dragging:
            fr, fc = divmod(self.drag["from"], 3)
            x, y = ox + fc * t + self.drag["dx"], oy + fr * t + self.drag["dy"]
            self.board.draw_tile(cr, self.logic.board[self.drag["from"]], x, y, t, 0.9)
            outline(cr, x, y, t, (1, 0.82, 0.2), 6)
