from gi.repository import Gdk, Gtk, Pango

from .dialogs import confirm, message, prompt_text
from .editor import fmt_duration

PATTERNS = ["*.mp3", "*.m4a", "*.aac", "*.wav", "*.ogg", "*.oga", "*.opus", "*.flac"]


class RecordingsWindow(Gtk.Window):
    def __init__(self, app, parent):
        super().__init__(transient_for=parent, title="Recordings", default_width=520, default_height=520)
        self.app = app
        header = Gtk.HeaderBar()
        add = Gtk.Button(label="Add recordings…")
        add.add_css_class("suggested-action")
        add.connect("clicked", self._choose)
        header.pack_start(add)
        self.set_titlebar(header)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("boxed-list")
        frame = Gtk.Frame(margin_top=12, margin_bottom=12, margin_start=12, margin_end=12, valign=Gtk.Align.START)
        frame.set_child(self.listbox)
        scroller = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(frame)
        hint = Gtk.Label(label="Tip: you can also drag audio files onto this window.", margin_bottom=10)
        hint.add_css_class("dim-label")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(scroller)
        box.append(hint)
        self.set_child(box)

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", lambda _t, value, _x, _y: self._import(value.get_files()) or True)
        self.add_controller(drop)

        self._changed = app.connect("changed", lambda *_: self.refresh())
        self.connect("unrealize", self._on_destroy)
        self.refresh()

    def _on_destroy(self, *_):
        self._alive = False
        self.app.disconnect(self._changed)
        self.app.preview.stop()

    _alive = True

    def refresh(self):
        if not self._alive:
            return
        while (r := self.listbox.get_row_at_index(0)) is not None:
            self.listbox.remove(r)
        if not self.app.settings.recordings:
            empty = Gtk.Label(label="No recordings yet.\nClick “Add recordings…” or drop audio files here.",
                              justify=Gtk.Justification.CENTER, margin_top=30, margin_bottom=30)
            empty.add_css_class("dim-label")
            self.listbox.append(empty)
            return
        for rec in self.app.settings.recordings:
            box = Gtk.Box(spacing=8, margin_top=8, margin_bottom=8, margin_start=10, margin_end=10)
            name = Gtk.Label(label=rec.name, xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END)
            dur = Gtk.Label(label=fmt_duration(rec.duration))
            dur.add_css_class("dim-label")
            playing = self.app.preview.playing == self.app.recording_path(rec)
            play = Gtk.Button(label="■ Stop" if playing else "▶ Preview")
            play.connect("clicked", self._preview, rec)
            rename = Gtk.Button(label="Rename")
            rename.connect("clicked", self._rename, rec)
            delete = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Delete")
            delete.connect("clicked", self._delete, rec)
            for w in (name, dur, play, rename, delete):
                box.append(w)
            self.listbox.append(box)

    def _preview(self, _btn, rec):
        path = self.app.recording_path(rec)
        if self.app.preview.playing == path:
            self.app.preview.stop()
        else:
            self.app.preview.play(path, restore=self.refresh)
        self.refresh()

    def _rename(self, _btn, rec):
        def done(text):
            rec.name = text
            self.app.save()
        prompt_text(self, "Rename recording", rec.name, done)

    def _delete(self, _btn, rec):
        confirm(self, f"Delete “{rec.name}”?",
                "It will also be removed from every alarm that uses it.", "Delete",
                lambda: self.app.delete_recording(rec))

    def _choose(self, *_):
        chooser = Gtk.FileChooserNative.new("Add recordings", self, Gtk.FileChooserAction.OPEN, "Add", "Cancel")
        chooser.set_select_multiple(True)
        f = Gtk.FileFilter()
        f.set_name("Audio files")
        for p in PATTERNS:
            f.add_pattern(p)
            f.add_pattern(p.upper())
        chooser.add_filter(f)

        def response(c, r):
            if r == Gtk.ResponseType.ACCEPT:
                model = c.get_files()
                self._import([model.get_item(i) for i in range(model.get_n_items())])
            self._chooser = None

        chooser.connect("response", response)
        self._chooser = chooser
        chooser.show()

    def _import(self, files):
        errors = self.app.import_files(files)
        if errors:
            message(self, "Some files weren't added",
                    "\n".join(errors) + "\n\nSupported: MP3, M4A, AAC, WAV, OGG, OPUS and FLAC.")
