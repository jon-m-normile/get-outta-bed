# Lessons

## Never synthesize input on the user's real display
- **What happened (2026-10-16):** to reproduce a click bug, I opened a fullscreen test window on the live desktop and sent it real XTest mouse clicks. The user saw the screen switch away under them and thought a Firefox window had been closed. It hadn't, but a stray click could have hit another app.
- **Rule:** any GUI test that sends input (clicks, keys, pointer motion) runs on an isolated virtual display: `xvfb-run -a -s "-screen 0 1280x800x24" env GDK_BACKEND=x11 ...`. Fullscreen test windows (the ring screen) also go on Xvfb, because they take over the user's screen.
- **Also:** test instances must use `Gio.ApplicationFlags.NON_UNIQUE`. Otherwise they forward to the user's running copy and pop its window up.
