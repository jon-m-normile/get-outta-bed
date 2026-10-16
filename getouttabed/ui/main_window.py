from datetime import timedelta

from gi.repository import Gio, GLib, Gtk, Pango

from .. import APP_NAME, scheduler
from ..model import PUZZLE_NAMES, Alarm, format_time


def next_alarm_text(app) -> str:
    nxt = scheduler.next_alarm(app.settings.alarms, app.now(), app.tz)
    if not nxt:
        return "No alarms scheduled"
    when = nxt[1].astimezone(app.tz)
    today = app.now().astimezone(app.tz).date()
    if when.date() == today:
        day = "Today"
    elif when.date() == today + timedelta(days=1):
        day = "Tomorrow"
    elif when.date() < today + timedelta(days=7):
        day = when.strftime("%A")
    else:
        day = f"{when.strftime('%a, %b')} {when.day}"
    return f"Next alarm: {day} {format_time(when.hour, when.minute)}"


class AlarmRow(Gtk.ListBoxRow):
    def __init__(self, app, alarm: Alarm):
        super().__init__()
        self.alarm = alarm
        box = Gtk.Box(spacing=12, margin_top=10, margin_bottom=10, margin_start=14, margin_end=14)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
        time = Gtk.Label(label=alarm.time_text(), xalign=0)
        time.add_css_class("alarm-time")
        text.append(time)
        if alarm.label:
            lbl = Gtk.Label(label=alarm.label, xalign=0, ellipsize=Pango.EllipsizeMode.END)
            lbl.add_css_class("alarm-label")
            text.append(lbl)
        detail = Gtk.Label(label=f"{alarm.summary()}  ·  {PUZZLE_NAMES.get(alarm.puzzle, 'Surprise me')}",
                           xalign=0, wrap=True)
        detail.add_css_class("alarm-detail")
        text.append(detail)
        box.append(text)
        switch = Gtk.Switch(active=alarm.enabled, valign=Gtk.Align.CENTER)
        switch.connect("notify::active", lambda s, _p: GLib.idle_add(app.set_enabled, alarm, s.get_active()))
        box.append(switch)
        if not alarm.enabled:
            self.add_css_class("alarm-off")
        self.set_child(box)


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME, default_width=480, default_height=600,
                         hide_on_close=True)
        self.app = app

        header = Gtk.HeaderBar()
        add = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add alarm")
        add.connect("clicked", lambda *_: self.open_editor(None))
        header.pack_start(add)

        menu = Gio.Menu()
        menu.append("About Get Outta Bed!", "app.about")
        menu.append("Quit", "app.quit")
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu, tooltip_text="Menu"))
        photo = Gtk.Button(label="Puzzle photo")
        photo.connect("clicked", self._open_photo)
        header.pack_end(photo)
        recs = Gtk.Button(label="Recordings")
        recs.connect("clicked", self._open_recordings)
        header.pack_end(recs)
        self.set_titlebar(header)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("boxed-list")
        self.listbox.connect("row-activated", lambda _lb, row: self.open_editor(row.alarm))
        scroller = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        frame = Gtk.Frame(margin_top=12, margin_bottom=6, margin_start=12, margin_end=12, valign=Gtk.Align.START)
        frame.set_child(self.listbox)
        scroller.set_child(frame)

        empty = Gtk.Label(label="No alarms yet — add one with +", vexpand=True)
        empty.add_css_class("empty-state")

        self.stack = Gtk.Stack()
        self.stack.add_named(empty, "empty")
        self.stack.add_named(scroller, "list")

        self.next_label = Gtk.Label()
        self.next_label.add_css_class("next-alarm")

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self.stack)
        content.append(Gtk.Separator())
        content.append(self.next_label)
        self.set_child(content)

        self._recordings = None
        app.connect("changed", lambda *_: self.refresh())
        GLib.timeout_add_seconds(30, self._tick)
        self.refresh()

    def _tick(self):
        self.next_label.set_label(next_alarm_text(self.app))
        return True

    def refresh(self):
        while (row := self.listbox.get_row_at_index(0)) is not None:
            self.listbox.remove(row)
        alarms = sorted(self.app.settings.alarms, key=lambda a: (a.hour, a.minute, a.label))
        for a in alarms:
            self.listbox.append(AlarmRow(self.app, a))
        self.stack.set_visible_child_name("list" if alarms else "empty")
        self.next_label.set_label(next_alarm_text(self.app))

    def open_editor(self, alarm):
        from .editor import AlarmEditor
        AlarmEditor(self.app, self, alarm).present()

    def _open_recordings(self, *_):
        from .recordings import RecordingsWindow
        if self._recordings is None:
            self._recordings = RecordingsWindow(self.app, self)
            self._recordings.connect("unrealize", lambda *_: setattr(self, "_recordings", None))
        self._recordings.present()

    def _open_photo(self, *_):
        from .photo import PhotoDialog
        PhotoDialog(self.app, self).present()
