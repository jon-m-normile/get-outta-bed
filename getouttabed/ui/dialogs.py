from gi.repository import Gtk


def confirm(parent, text: str, secondary: str, action: str, on_yes) -> None:
    dlg = Gtk.MessageDialog(transient_for=parent, modal=True, message_type=Gtk.MessageType.QUESTION,
                            text=text, secondary_text=secondary)
    dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
    btn = dlg.add_button(action, Gtk.ResponseType.ACCEPT)
    btn.add_css_class("destructive-action")

    def response(d, r):
        d.destroy()
        if r == Gtk.ResponseType.ACCEPT:
            on_yes()

    dlg.connect("response", response)
    dlg.present()


def message(parent, text: str, secondary: str = "") -> None:
    dlg = Gtk.MessageDialog(transient_for=parent, modal=True, message_type=Gtk.MessageType.WARNING,
                            buttons=Gtk.ButtonsType.OK, text=text, secondary_text=secondary or None)
    dlg.connect("response", lambda d, r: d.destroy())
    dlg.present()


def prompt_text(parent, title: str, initial: str, on_ok) -> None:
    win = Gtk.Window(transient_for=parent, modal=True, title=title, default_width=360, resizable=False)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=18, margin_bottom=18,
                  margin_start=18, margin_end=18)
    entry = Gtk.Entry(text=initial, activates_default=True)
    box.append(entry)
    buttons = Gtk.Box(spacing=8, halign=Gtk.Align.END)
    cancel = Gtk.Button(label="Cancel")
    ok = Gtk.Button(label="Save")
    ok.add_css_class("suggested-action")
    buttons.append(cancel)
    buttons.append(ok)
    box.append(buttons)
    win.set_child(box)
    win.set_default_widget(ok)

    def done(*_):
        text = entry.get_text().strip()
        win.destroy()
        if text:
            on_ok(text)

    ok.connect("clicked", done)
    cancel.connect("clicked", lambda *_: win.destroy())
    win.present()
    entry.grab_focus()


def date_button(initial, on_change):
    """A MenuButton showing a date, with a calendar popover. Returns (button, setter)."""
    from datetime import date
    from gi.repository import GLib
    btn = Gtk.MenuButton()
    cal = Gtk.Calendar()
    pop = Gtk.Popover()
    pop.set_child(cal)
    btn.set_popover(pop)
    state = {"busy": False}

    def show(d):
        btn.set_label(f"{d.strftime('%a, %b')} {d.day}, {d.year}")

    def set_date(d):
        state["busy"] = True
        cal.select_day(GLib.DateTime.new_local(d.year, d.month, d.day, 0, 0, 0))
        state["busy"] = False
        show(d)

    def picked(c):
        if state["busy"]:
            return
        g = c.get_date()
        d = date(g.get_year(), g.get_month(), g.get_day_of_month())
        show(d)
        pop.popdown()
        on_change(d)

    cal.connect("day-selected", picked)
    set_date(initial)
    return btn, set_date
