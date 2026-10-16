import copy

from gi.repository import Gdk, GObject, Gtk, Pango

from .. import audio, recurrence
from ..model import PUZZLES, Alarm
from .dialogs import confirm, date_button

CUSTOM = "__custom__"


def preset_kind(rule):
    if not rule:
        return "none"
    p = recurrence.parse_parts(rule)
    if set(p) - {"FREQ", "BYDAY", "BYMONTH", "BYMONTHDAY"}:
        return "custom"
    if p["FREQ"] == "WEEKLY" and "," not in p.get("BYDAY", ""):
        return "weekly"
    if p["FREQ"] == "MONTHLY" and p.get("BYDAY", "").startswith("-1"):
        return "monthly-last"
    if p["FREQ"] == "MONTHLY" and "BYDAY" in p:
        return "monthly-nth"
    if p["FREQ"] == "YEARLY":
        return "annual"
    return "other"


def fmt_duration(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


class AlarmEditor(Gtk.Window):
    def __init__(self, app, parent, alarm):
        super().__init__(transient_for=parent, modal=True, default_width=560, default_height=780,
                         title="New Alarm" if alarm is None else "Edit Alarm")
        self.app = app
        self.is_new = alarm is None
        now = app.now().astimezone(app.tz)
        self.alarm = copy.deepcopy(alarm) if alarm else Alarm(
            start_date=recurrence.default_start_date(7, 0, now).isoformat())
        self.rule = self.alarm.rrule
        self.start = self.alarm.start
        self.date_touched = not self.is_new
        lib = [r.id for r in app.settings.recordings]
        self.checked = {rid for rid in self.alarm.recordings if rid in lib}
        self.order = [rid for rid in self.alarm.recordings if rid in lib] + \
                     [rid for rid in lib if rid not in self.checked]
        self._building = False

        grid = Gtk.Grid(column_spacing=14, row_spacing=14, margin_top=18, margin_bottom=18,
                        margin_start=18, margin_end=18)
        row = 0

        def add(label, widget):
            nonlocal row
            lbl = Gtk.Label(label=label, xalign=1, valign=Gtk.Align.CENTER)
            lbl.add_css_class("dim-label")
            grid.attach(lbl, 0, row, 1, 1)
            grid.attach(widget, 1, row, 1, 1)
            row += 1

        # Time
        h12 = self.alarm.hour % 12 or 12
        self.hour = Gtk.SpinButton.new_with_range(1, 12, 1)
        self.hour.set_value(h12)
        self.minute = Gtk.SpinButton.new_with_range(0, 59, 1)
        self.minute.set_value(self.alarm.minute)
        for s in (self.hour, self.minute):
            s.set_wrap(True)
            s.set_numeric(True)
            s.add_css_class("big-spin")
            s.set_orientation(Gtk.Orientation.VERTICAL)
        self.minute.connect("output", self._pad_minute)
        self._pad_minute(self.minute)
        self.am = Gtk.ToggleButton(label="AM", active=self.alarm.hour < 12)
        self.pm = Gtk.ToggleButton(label="PM", active=self.alarm.hour >= 12, group=self.am)
        ampm = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        ampm.add_css_class("linked")
        ampm.append(self.am)
        ampm.append(self.pm)
        tbox = Gtk.Box(spacing=8)
        tbox.append(self.hour)
        colon = Gtk.Label(label=":")
        colon.add_css_class("big-spin")
        tbox.append(colon)
        tbox.append(self.minute)
        tbox.append(ampm)
        for w in (self.hour, self.minute):
            w.connect("value-changed", self._time_changed)
        self.am.connect("toggled", self._time_changed)
        add("Time", tbox)

        # Label
        self.label = Gtk.Entry(text=self.alarm.label, placeholder_text="e.g. School", hexpand=True)
        add("Label", self.label)

        # Start date
        self.date_btn, self.set_date = date_button(self.start, self._date_picked)
        self.date_btn.set_halign(Gtk.Align.START)
        add("Starts", self.date_btn)

        # Repeat
        self.repeat = Gtk.DropDown(hexpand=True)
        self.repeat.connect("notify::selected", self._repeat_selected)
        add("Repeat", self.repeat)
        self._rebuild_repeat()

        # Volume
        vbox = Gtk.Box(spacing=8)
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 5)
        self.volume.set_value(self.alarm.max_volume)
        self.volume.set_hexpand(True)
        self.volume.set_draw_value(True)
        self.volume.set_format_value_func(lambda _s, v: f"{int(v)}%")
        test = Gtk.Button(label="▶ Test", valign=Gtk.Align.CENTER, tooltip_text="Play the first message at this volume for 5 seconds")
        test.connect("clicked", self._test_volume)
        vbox.append(self.volume)
        vbox.append(test)
        add("Maximum volume", vbox)

        # Puzzle
        self.puzzle = Gtk.DropDown.new_from_strings([name for _, name in PUZZLES])
        keys = [k for k, _ in PUZZLES]
        self.puzzle.set_selected(keys.index(self.alarm.puzzle) if self.alarm.puzzle in keys else len(keys) - 1)
        add("Puzzle", self.puzzle)

        # Messages
        title = Gtk.Label(label="Messages", xalign=0)
        title.add_css_class("section-title")
        grid.attach(title, 0, row, 2, 1)
        row += 1
        self.in_order = Gtk.ToggleButton(label="Play in order", active=not self.alarm.shuffle)
        self.shuffle = Gtk.ToggleButton(label="Shuffle", active=self.alarm.shuffle, group=self.in_order)
        mode = Gtk.Box(halign=Gtk.Align.START)
        mode.add_css_class("linked")
        mode.append(self.in_order)
        mode.append(self.shuffle)
        grid.attach(mode, 0, row, 2, 1)
        row += 1
        self.repeat = Gtk.SpinButton.new_with_range(1, 10, 1)
        self.repeat.set_value(self.alarm.repeat)
        self.pause = Gtk.SpinButton.new_with_range(0, 60, 0.5)
        self.pause.set_digits(1)
        self.pause.set_value(self.alarm.pause)
        for text, spin, unit in (("Play each message", self.repeat, "times"),
                                 ("Pause between messages", self.pause, "seconds")):
            line = Gtk.Box(spacing=8)
            line.append(spin)
            line.append(Gtk.Label(label=unit))
            add(text, line)
        self.messages = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.messages.add_css_class("boxed-list")
        frame = Gtk.Frame()
        frame.set_child(self.messages)
        grid.attach(frame, 0, row, 2, 1)
        row += 1
        hint = Gtk.Label(label="Checked messages play in this order, then loop. Drag to reorder. "
                               "With none checked, a built-in alarm tone plays.",
                         xalign=0, wrap=True)
        hint.add_css_class("dim-label")
        grid.attach(hint, 0, row, 2, 1)
        row += 1
        self._rebuild_messages()

        scroller = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(grid)

        actions = Gtk.Box(spacing=8, margin_top=10, margin_bottom=12, margin_start=18, margin_end=18)
        ring = Gtk.Button(label="Ring now (test)")
        ring.connect("clicked", self._ring_now)
        actions.append(ring)
        if not self.is_new:
            delete = Gtk.Button(label="Delete")
            delete.add_css_class("destructive-action")
            delete.connect("clicked", self._delete)
            actions.append(delete)
        actions.append(Gtk.Box(hexpand=True))
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda *_: self.close())
        save = Gtk.Button(label="Save")
        save.add_css_class("suggested-action")
        save.connect("clicked", self._save)
        actions.append(cancel)
        actions.append(save)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(scroller)
        box.append(Gtk.Separator())
        box.append(actions)
        self.set_child(box)
        self.connect("close-request", self._on_close)

    def _on_close(self, *_):
        self.app.preview.stop()
        return False

    # --- time & date -----------------------------------------------------

    @staticmethod
    def _pad_minute(spin):
        spin.set_text(f"{int(spin.get_value()):02d}")
        return True

    def _hour24(self) -> int:
        h = int(self.hour.get_value()) % 12
        return h + 12 if self.pm.get_active() else h

    def _time_changed(self, *_):
        if self.date_touched:
            return
        now = self.app.now().astimezone(self.app.tz)
        d = recurrence.default_start_date(self._hour24(), int(self.minute.get_value()), now)
        if d != self.start:
            self.set_date(d)
            self._date_changed(d)

    def _date_picked(self, d):
        self.date_touched = True
        self._date_changed(d)

    def _date_changed(self, d):
        old_presets = dict((r, k) for k, r in recurrence.presets(self.start))
        kind = preset_kind(self.rule)
        self.start = d
        if self.rule in old_presets and kind in ("weekly", "monthly-nth", "monthly-last", "annual"):
            by_kind = {preset_kind(r): r for _label, r in reversed(recurrence.presets(d))}
            fallback = {"monthly-nth": "monthly-last", "monthly-last": "monthly-nth"}.get(kind)
            self.rule = by_kind.get(kind) or by_kind.get(fallback) or self.rule
        self._rebuild_repeat()

    # --- repeat ----------------------------------------------------------

    def _rebuild_repeat(self):
        items = recurrence.presets(self.start)
        if self.rule not in [r for _, r in items]:
            items.append((recurrence.describe(self.rule, self.start, long=True), self.rule))
        items.append(("Custom…", CUSTOM))
        self.repeat_items = items
        self._building = True
        self.repeat.set_model(Gtk.StringList.new([label for label, _ in items]))
        self.repeat.set_selected([r for _, r in items].index(self.rule))
        self._building = False

    def _repeat_selected(self, *_):
        if self._building:
            return
        idx = self.repeat.get_selected()
        if idx >= len(self.repeat_items):
            return
        rule = self.repeat_items[idx][1]
        if rule != CUSTOM:
            self.rule = rule
            return
        from .custom_repeat import CustomRepeatDialog
        CustomRepeatDialog(self, self.rule, self.start, self._custom_done).present()

    def _custom_done(self, rule):
        if rule is not None:
            self.rule = rule
        self._rebuild_repeat()

    # --- messages --------------------------------------------------------

    def _rebuild_messages(self):
        while (r := self.messages.get_row_at_index(0)) is not None:
            self.messages.remove(r)
        if not self.order:
            empty = Gtk.Label(label="No recordings yet — add some with the Recordings button.",
                              margin_top=12, margin_bottom=12, wrap=True)
            empty.add_css_class("dim-label")
            self.messages.append(empty)
            return
        for rid in self.order:
            rec = self.app.settings.recording(rid)
            row = Gtk.ListBoxRow(activatable=False)
            box = Gtk.Box(spacing=10, margin_top=6, margin_bottom=6, margin_start=8, margin_end=8)
            handle = Gtk.Label(label="⠿", tooltip_text="Drag to reorder")
            handle.add_css_class("drag-handle")
            check = Gtk.CheckButton(active=rid in self.checked)
            check.connect("toggled", self._toggle_message, rid)
            name = Gtk.Label(label=rec.name, xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END)
            dur = Gtk.Label(label=fmt_duration(rec.duration))
            dur.add_css_class("dim-label")
            for w in (handle, check, name, dur):
                box.append(w)
            row.set_child(box)

            src = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
            src.connect("prepare", lambda *_a, rid=rid: Gdk.ContentProvider.new_for_value(rid))
            row.add_controller(src)
            dst = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
            dst.connect("drop", self._drop, rid)
            dst.connect("enter", lambda t, *_a: (t.get_widget().add_css_class("drop-target"), Gdk.DragAction.MOVE)[1])
            dst.connect("leave", lambda t: t.get_widget().remove_css_class("drop-target"))
            row.add_controller(dst)
            self.messages.append(row)

    def _toggle_message(self, check, rid):
        if check.get_active():
            self.checked.add(rid)
        else:
            self.checked.discard(rid)

    def _drop(self, target, value, _x, y, onto):
        target.get_widget().remove_css_class("drop-target")
        if value == onto or value not in self.order:
            return False
        self.order.remove(value)
        idx = self.order.index(onto)
        if y > target.get_widget().get_height() / 2:
            idx += 1
        self.order.insert(idx, value)
        self._rebuild_messages()
        return True

    # --- actions ---------------------------------------------------------

    def collect(self) -> Alarm:
        a = copy.deepcopy(self.alarm)
        a.hour, a.minute = self._hour24(), int(self.minute.get_value())
        a.label = self.label.get_text().strip()
        a.rrule = self.rule
        a.start_date = self.start.isoformat()
        a.max_volume = int(self.volume.get_value())
        a.recordings = [rid for rid in self.order if rid in self.checked]
        a.shuffle = self.shuffle.get_active()
        a.repeat = int(self.repeat.get_value())
        a.pause = self.pause.get_value()
        a.puzzle = PUZZLES[self.puzzle.get_selected()][0]
        return a

    def _test_volume(self, *_):
        a = self.collect()
        files = self.app.playlist_files(a)
        self.app.test_volume(files[0] if files else audio.fallback_tone(), a.max_volume)

    def _ring_now(self, *_):
        self.app.ring(self.collect(), test=True)

    def _save(self, *_):
        self.app.preview.stop()
        self.app.save_alarm(self.collect())
        self.destroy()

    def _delete(self, *_):
        def do():
            self.app.delete_alarm(self.alarm)
            self.destroy()
        confirm(self, "Delete this alarm?", f"{self.alarm.time_text()} {self.alarm.label}".strip(), "Delete", do)
