import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from .. import paths  # noqa: E402
from ..log import log  # noqa: E402
from .dialogs import message  # noqa: E402

PHOTO_SIZE = 900


def load_photo(size: int = PHOTO_SIZE) -> GdkPixbuf.Pixbuf:
    """The current puzzle photo as a square pixbuf, falling back to the bundled picture."""
    for path in (paths.photo_file(), paths.DEFAULT_PHOTO):
        try:
            if path.exists():
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, size, False)
        except GLib.Error as e:
            log(f"ERROR loading puzzle photo {path}: {e.message}")
    pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, size, size)
    pb.fill(0x3366ccff)
    return pb


def save_square(src: str) -> None:
    """Center-crop to a square, downscale to ~900 px and save as puzzle-photo.jpg."""
    pb = GdkPixbuf.Pixbuf.new_from_file(src)
    pb = pb.apply_embedded_orientation() or pb
    w, h = pb.get_width(), pb.get_height()
    side = min(w, h)
    pb = pb.new_subpixbuf((w - side) // 2, (h - side) // 2, side, side)
    if side > PHOTO_SIZE:
        pb = pb.scale_simple(PHOTO_SIZE, PHOTO_SIZE, GdkPixbuf.InterpType.HYPER)
    if pb.get_has_alpha():
        flat = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, pb.get_width(), pb.get_height())
        flat.fill(0xffffffff)
        pb.composite(flat, 0, 0, pb.get_width(), pb.get_height(), 0, 0, 1, 1, GdkPixbuf.InterpType.NEAREST, 255)
        pb = flat
    dest = paths.photo_file()
    tmp = dest.with_name("puzzle-photo.tmp.jpg")
    pb.savev(str(tmp), "jpeg", ["quality"], ["90"])
    tmp.replace(dest)


def heif_supported() -> bool:
    return any("heif" in f.get_name() for f in GdkPixbuf.Pixbuf.get_formats())


class PhotoDialog(Gtk.Window):
    def __init__(self, app, parent):
        super().__init__(transient_for=parent, modal=True, title="Puzzle photo", resizable=False)
        self.app = app
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=18, margin_bottom=18,
                      margin_start=18, margin_end=18)
        self.picture = Gtk.Picture(can_shrink=True)
        self.picture.set_size_request(320, 320)
        box.append(self.picture)
        self.caption = Gtk.Label()
        self.caption.add_css_class("dim-label")
        box.append(self.caption)
        buttons = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        choose = Gtk.Button(label="Choose photo…")
        choose.add_css_class("suggested-action")
        choose.connect("clicked", self._choose)
        reset = Gtk.Button(label="Reset to default")
        reset.connect("clicked", self._reset)
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda *_: self.destroy())
        for b in (choose, reset, close):
            buttons.append(b)
        box.append(buttons)
        self.set_child(box)
        self._show()

    def _show(self):
        self.picture.set_paintable(Gdk.Texture.new_for_pixbuf(load_photo(320)))
        self.caption.set_label("Your photo" if paths.photo_file().exists() else "Default picture")

    def _choose(self, *_):
        chooser = Gtk.FileChooserNative.new("Choose a photo", self, Gtk.FileChooserAction.OPEN, "Choose", "Cancel")
        f = Gtk.FileFilter()
        f.set_name("Photos")
        exts = ["jpg", "jpeg", "png"] + (["heic", "heif"] if heif_supported() else [])
        for e in exts:
            f.add_pattern(f"*.{e}")
            f.add_pattern(f"*.{e.upper()}")
        chooser.add_filter(f)

        def response(c, r):
            self._chooser = None
            if r != Gtk.ResponseType.ACCEPT:
                return
            path = c.get_file().get_path()
            try:
                save_square(path)
                log(f"puzzle photo set from {path}")
            except GLib.Error as e:
                message(self, "That photo couldn't be opened", e.message)
            self._show()

        chooser.connect("response", response)
        self._chooser = chooser
        chooser.show()

    def _reset(self, *_):
        try:
            paths.photo_file().unlink()
        except FileNotFoundError:
            pass
        self._show()
