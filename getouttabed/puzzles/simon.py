from gi.repository import GLib, Gtk

from .base import Puzzle
from .logic import SimonLogic

FLASH_INTERVAL_MS = 600
FLASH_ON_MS = 400


class Simon(Puzzle):
    title = "Simon"

    def __init__(self, ctx):
        super().__init__(ctx)
        grid = Gtk.Grid(row_spacing=16, column_spacing=16, halign=Gtk.Align.CENTER)
        self.pads = []
        for i in range(4):
            b = Gtk.Button()
            b.add_css_class("simon-pad")
            b.add_css_class(f"simon-{i}")
            b.connect("clicked", self._pressed, i)
            grid.attach(b, i % 2, i // 2, 1, 1)
            self.pads.append(b)
        self.append(grid)
        self.play_btn = Gtk.Button(label="▶ Play pattern", halign=Gtk.Align.CENTER)
        self.play_btn.add_css_class("simon-play")
        self.play_btn.connect("clicked", lambda *_: self._play())
        self.append(self.play_btn)
        self.feedback = Gtk.Label()
        self.feedback.add_css_class("puzzle-feedback")
        self.append(self.feedback)
        self._sources = []
        self.accepting = True
        self.logic = SimonLogic()
        self._dots()

    def start(self):
        self.feedback.set_label("Press “Play pattern” to see it — as many times as you like.")

    def reset(self):
        super().reset()
        self._cancel()
        self._your_turn()
        self.logic = SimonLogic()
        self._dots()
        self.start()

    def _later(self, ms, fn, *args):
        sid = None

        def run():
            self._sources.remove(sid)
            fn(*args)
            return False

        sid = GLib.timeout_add(ms, run)
        self._sources.append(sid)

    def _cancel(self):
        for s in self._sources:
            GLib.source_remove(s)
        self._sources = []

    def _dots(self):
        done = self.logic.position
        self.progress.set_label(" ".join("●" if i < done else "○" for i in range(SimonLogic.LENGTH)))

    def _play(self, delay=600):
        """Shows the pattern with the alarm messages silenced; the player can ask for it any number of times."""
        self._cancel()
        self.accepting = False
        self.play_btn.set_sensitive(False)
        self.ctx.duck(True)
        self.logic.position = 0
        self.feedback.set_label("Watch the pattern…")
        self._dots()
        for k, pad in enumerate(self.logic.sequence):
            self._later(delay + k * FLASH_INTERVAL_MS, self._flash, pad)
        self._later(delay + len(self.logic.sequence) * FLASH_INTERVAL_MS, self._your_turn)

    def _your_turn(self):
        self.accepting = True
        self.play_btn.set_sensitive(True)
        self.ctx.duck(False)
        self.feedback.set_label("Your turn — repeat the pattern.")

    def _flash(self, pad):
        b = self.pads[pad]
        b.add_css_class("lit")
        self.ctx.effects.play(f"simon-{pad}.wav")
        GLib.timeout_add(FLASH_ON_MS, lambda: b.remove_css_class("lit") or False)

    def _pressed(self, _b, pad):
        if not self.accepting:
            return
        self._flash(pad)
        result = self.logic.press(pad)
        self._dots()
        if result == "solved":
            self.accepting = False
            self.play_btn.set_sensitive(False)
            self.feedback.set_label("You got it!")
            self.finish(700)
        elif result == "mistake":
            left = 3 - self.logic.failures
            self.feedback.set_label(f"Oops — start again from the first color. "
                                    f"({left} {'try' if left == 1 else 'tries'} before a new pattern)")
        elif result == "reset":
            self.feedback.set_label("New pattern! Press “Play pattern” to see it.")
