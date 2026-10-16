from gi.repository import GLib, Gtk

from .base import Puzzle
from .logic import MathLogic


class MathPuzzle(Puzzle):
    title = "Math"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.problem = Gtk.Label()
        self.problem.add_css_class("math-problem")
        self.append(self.problem)
        self.entry = Gtk.Entry(width_chars=6, max_length=5, xalign=0.5, halign=Gtk.Align.CENTER,
                               input_purpose=Gtk.InputPurpose.NUMBER)
        self.entry.add_css_class("math-entry")
        self.entry.connect("activate", self._submit)
        self.append(self.entry)
        self.feedback = Gtk.Label(label="Type the answer and press Enter.")
        self.feedback.add_css_class("puzzle-feedback")
        self.append(self.feedback)
        self._shake_id = None
        self.reset()

    def start(self):
        self.entry.grab_focus()

    def reset(self):
        super().reset()
        self.logic = MathLogic()
        self._show()

    def _show(self):
        if self.logic.solved:
            self.progress.set_label("3 / 3 solved")
            return
        self.problem.set_label(self.logic.current.text())
        self.progress.set_label(f"Problem {self.logic.index + 1} of {MathLogic.COUNT}")
        self.entry.set_text("")
        self.entry.grab_focus()

    def _submit(self, *_):
        if self.logic.solved:
            return
        typed = self.entry.get_text()
        if not typed.strip():
            return
        result = self.logic.submit(typed)
        if result == "solved":
            self.feedback.set_label("Correct!")
            self.entry.set_sensitive(False)
            self.finish(600)
        elif result == "correct":
            self.feedback.set_label("Correct! Next one:")
        elif result == "wrong":
            self.feedback.set_label("Not quite. Here's a new one.")
            self._shake()
        else:
            self.feedback.set_label("Let's start a fresh set of 3.")
            self._shake()
        self._show()

    def _shake(self):
        if self._shake_id:
            GLib.source_remove(self._shake_id)
        offsets = iter([16, -16, 12, -12, 6, -6, 0])

        def step():
            try:
                off = next(offsets)
            except StopIteration:
                self._shake_id = None
                return False
            self.entry.set_margin_start(max(0, off) * 2)
            self.entry.set_margin_end(max(0, -off) * 2)
            return True

        self._shake_id = GLib.timeout_add(40, step)
