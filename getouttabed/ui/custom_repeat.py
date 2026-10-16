from datetime import date, timedelta

from gi.repository import Gtk

from .. import recurrence
from ..recurrence import DAY_CODES, ORDINALS
from .dialogs import date_button

FREQS = ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
UNITS = ["day", "week", "month", "year"]
# Google-style week row, Sunday first.
WEEK_ROW = [("S", "SU"), ("M", "MO"), ("T", "TU"), ("W", "WE"), ("T", "TH"), ("F", "FR"), ("S", "SA")]


class CustomRepeatDialog(Gtk.Window):
    def __init__(self, parent, rule, start: date, on_done):
        super().__init__(transient_for=parent, modal=True, title="Custom repeat", resizable=False,
                         default_width=420)
        self.start = start
        self.on_done = on_done
        self._finished = False
        p = recurrence.parse_parts(rule) if rule else {"FREQ": "WEEKLY"}
        freq = p.get("FREQ", "WEEKLY")
        n, is_last = recurrence.nth_weekday(start)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin_top=18, margin_bottom=18,
                      margin_start=18, margin_end=18)

        every = Gtk.Box(spacing=8)
        every.append(Gtk.Label(label="Repeat every"))
        self.interval = Gtk.SpinButton.new_with_range(1, 99, 1)
        self.interval.set_value(int(p.get("INTERVAL", 1)))
        every.append(self.interval)
        self.unit = Gtk.DropDown()
        every.append(self.unit)
        box.append(every)

        # Weekly
        self.week_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.week_box.append(Gtk.Label(label="Repeat on", xalign=0))
        days = Gtk.Box(spacing=4)
        selected = set(p.get("BYDAY", "").split(",")) if freq == "WEEKLY" and "BYDAY" in p \
            else {DAY_CODES[start.weekday()]}
        self.day_buttons = {}
        for letter, code in WEEK_ROW:
            b = Gtk.ToggleButton(label=letter, active=code in selected,
                                 tooltip_text=recurrence.DAY_NAMES[DAY_CODES.index(code)])
            b.set_size_request(40, 40)
            b.connect("toggled", self._day_toggled)
            self.day_buttons[code] = b
            days.append(b)
        self.week_box.append(days)
        box.append(self.week_box)

        # Monthly
        weekday = recurrence.DAY_NAMES[start.weekday()]
        self.month_options = [("day", f"Monthly on day {start.day}")]
        if n <= 4:
            self.month_options.append((f"{n}{DAY_CODES[start.weekday()]}", f"Monthly on the {ORDINALS[n]} {weekday}"))
        if is_last:
            self.month_options.append((f"-1{DAY_CODES[start.weekday()]}", f"Monthly on the last {weekday}"))
        self.month = Gtk.DropDown.new_from_strings([label for _, label in self.month_options])
        if freq == "MONTHLY" and "BYDAY" in p:
            keys = [k for k, _ in self.month_options]
            self.month.set_selected(keys.index(p["BYDAY"]) if p["BYDAY"] in keys else min(1, len(keys) - 1))
        self.month.set_halign(Gtk.Align.START)
        box.append(self.month)

        # Ends
        ends = Gtk.Grid(column_spacing=8, row_spacing=8)
        ends.attach(Gtk.Label(label="Ends", xalign=0), 0, 0, 3, 1)
        self.never = Gtk.CheckButton(label="Never", active=True)
        self.on = Gtk.CheckButton(label="On", group=self.never)
        self.after = Gtk.CheckButton(label="After", group=self.never)
        until = start + timedelta(days=90)
        if "UNTIL" in p:
            from datetime import datetime
            until = datetime.strptime(p["UNTIL"][:8], "%Y%m%d").date()
            self.on.set_active(True)
        self.until = until
        self.until_btn, _ = date_button(until, self._until_picked)
        self.count = Gtk.SpinButton.new_with_range(1, 999, 1)
        self.count.set_value(int(p.get("COUNT", 13)))
        if "COUNT" in p:
            self.after.set_active(True)
        ends.attach(self.never, 0, 1, 1, 1)
        ends.attach(self.on, 0, 2, 1, 1)
        ends.attach(self.until_btn, 1, 2, 2, 1)
        ends.attach(self.after, 0, 3, 1, 1)
        ends.attach(self.count, 1, 3, 1, 1)
        ends.attach(Gtk.Label(label="occurrences", xalign=0), 2, 3, 1, 1)
        box.append(ends)

        self.summary = Gtk.Label(xalign=0, wrap=True)
        self.summary.add_css_class("dim-label")
        box.append(self.summary)

        buttons = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda *_: self.close())
        done = Gtk.Button(label="Done")
        done.add_css_class("suggested-action")
        done.connect("clicked", self._done)
        buttons.append(cancel)
        buttons.append(done)
        box.append(buttons)
        self.set_child(box)

        self._set_units(FREQS.index(freq) if freq in FREQS else 1)
        for w, sig in ((self.interval, "value-changed"), (self.unit, "notify::selected"),
                       (self.month, "notify::selected"), (self.never, "toggled"), (self.on, "toggled"),
                       (self.after, "toggled"), (self.count, "value-changed")):
            w.connect(sig, self._update)
        self.connect("close-request", self._closing)
        self._update()

    def _set_units(self, idx):
        plural = self.interval.get_value() > 1
        self._units_busy = True
        self.unit.set_model(Gtk.StringList.new([u + ("s" if plural else "") for u in UNITS]))
        self.unit.set_selected(idx)
        self._units_busy = False

    def _day_toggled(self, btn):
        if not any(b.get_active() for b in self.day_buttons.values()):
            btn.set_active(True)
            return
        self._update()

    def _until_picked(self, d):
        self.until = d
        self.on.set_active(True)
        self._update()

    def rule(self) -> str:
        freq = FREQS[self.unit.get_selected()]
        kw = {}
        if freq == "WEEKLY":
            kw["byday"] = [c for c in DAY_CODES if self.day_buttons[c].get_active()]
        elif freq == "MONTHLY":
            key = self.month_options[self.month.get_selected()][0]
            if key == "day":
                kw["bymonthday"] = self.start.day
            else:
                kw["byday"] = [key]
        elif freq == "YEARLY":
            kw["bymonth"], kw["bymonthday"] = self.start.month, self.start.day
        if self.on.get_active():
            kw["until"] = self.until
        elif self.after.get_active():
            kw["count"] = int(self.count.get_value())
        return recurrence.build_rule(freq, int(self.interval.get_value()), **kw)

    def _update(self, *_):
        if getattr(self, "_units_busy", False):
            return
        plural = self.interval.get_value() > 1
        if self.unit.get_model().get_string(0).endswith("s") != plural:
            self._set_units(self.unit.get_selected())
        freq = FREQS[self.unit.get_selected()]
        self.week_box.set_visible(freq == "WEEKLY")
        self.month.set_visible(freq == "MONTHLY")
        self.summary.set_label(recurrence.describe(self.rule(), self.start, long=True) + ".")

    def _done(self, *_):
        self._finished = True
        self.on_done(self.rule())
        self.destroy()

    def _closing(self, *_):
        if not self._finished:
            self._finished = True
            self.on_done(None)
        return False
