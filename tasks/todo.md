# Get Outta Bed! v1 — build plan

Target detected: elementary OS 7.1 (Ubuntu 22.04 base), Python 3.10, GTK 4.6, GStreamer 1.20.
Dev box is a Lenovo, not the iMac. All apt deps already present here; Granite-GTK4 absent (not used).
GTK 4.6 constraints: no Gtk.FileDialog/AlertDialog (use FileChooserNative / MessageDialog).

- [x] 1. Data model + recurrence (`model.py`, `recurrence.py`) with tests
- [x] 2. Scheduler + audio engine (`scheduler.py`, `audio.py`) with tests (catch-up, ramp)
- [x] 3. Main window + alarm editor + custom repeat dialog
- [x] 4. Recordings library + puzzle photo dialog
- [x] 5. Ringing screen (fullscreen, uncloseable, 60-min cap, logging)
- [x] 6. Five puzzles (logic in `puzzles/logic.py`, one UI file each) + tests
- [x] 7. Assets (icon, default photo, sounds), install.sh / uninstall.sh / README.md
- [x] 8. Smoke run of the app; acceptance checklist items that can be checked on this box

## Review

Results:
- 77 pytest tests pass. Run them with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q`; an unrelated anchorpy plugin on this box breaks autoload.
- Screenshots checked: main window, editor, custom repeat, recordings, photo dialog, and all 5 ringing puzzles. A forced solve on each puzzle reaches SOLVED, restores volume and closes.
- End to end, an alarm set 1 minute ahead fired on time from the background timer. It unmuted, ramped from the previous volume, and the one-time alarm switched itself off.
- An M4A file imports, probes and plays through Playlist with no fallback.
- install.sh was run twice into a sandbox HOME (fresh install, then upgrade) and kept settings. uninstall.sh was run twice, once with "n" (data kept) and once with "y" (data deleted). desktop-file-validate passes on both .desktop files.
- Bug fixed: in PyGObject on GTK4, a window's "destroy" signal doesn't fire while Python still holds a reference. Because of this, `app.ringing` never cleared and the Recordings window couldn't reopen. The ringing and recordings windows now clean up on "unrealize" instead (ringing.py:52, ringing.py:108, recordings.py:38, main_window.py:125).
- Not done here: install.sh has not been run for real on this machine, because it changes autostart and inhibits suspend. On this box it would `sudo apt install python3-dateutil`, since dateutil is currently pip-installed.
- Still open: the manual acceptance checklist (PRD §11) on the iMac, covering dock, reboot/autostart, loudness and locked-screen behavior.

## Fixes after release

- [x] 9. Recordings named with "#" (e.g. "Wake Up #1.FLAC") were rejected as "not a supported format". Cause: the portal file chooser (FileChooserNative) passes the path through a URI, and GIO drops everything after an unescaped "#", so the app received "Wake Up ". Fix: both choosers now use an in-process Gtk.FileChooserDialog (`choose_files` in ui/dialogs.py). A missing file now reports "couldn't be found" instead of "unsupported" (app.py). Verified by importing both FLAC files from ~/Downloads through the new chooser.
- [x] 10. Per-alarm message repeat count and pause. Each alarm now has "Play each message N times" (1–10) and "Pause between messages" (0–60 s, 0.5 s steps), set in the editor's Messages section. Repeats of the same message are 0.5 s apart; the pause applies before the next message. The defaults (1 time, 1.5 s) match the old behavior, so existing alarms are unchanged. Files: model.py (Alarm.repeat/pause), audio.py (Playlist), ui/editor.py, ui/ringing.py; new tests in tests/test_playlist.py. Real-time playback timing and an editor screenshot checked.
- [x] 11. The puzzle didn't respond after "Ring now (test)" from the alarm editor. Cause: in GTK 4, a modal window blocks input to every window in its window group. The editor is modal, so the fullscreen puzzle ignored clicks. A real alarm would do the same if any dialog were left open. Fix: RingWindow gets its own Gtk.WindowGroup (ringing.py:21). Verified with XTest clicks on an Xvfb virtual display in three cases: editor open, no dialog, and photo dialog plus a confirm dialog open.
- [x] 12. ✅ 24-hour clock only, so there's no AM/PM mistake. The editor's hour spin now runs 00–23 with zero padding and a "24-hour clock" hint. The AM/PM toggle is gone. `format_time` shows HH:MM everywhere: the alarm list, "Next alarm", the ring screen and the log. Files: model.py, ui/editor.py, tests/test_settings.py. Xvfb screenshots of the main window, editor and ring screen checked.
- [x] 13. ✅ The alarm wouldn't ring today after its time was edited: "Next alarm" stayed on Monday. Cause: when an existing alarm was edited, its start date was treated as hand-picked, so changing the time never moved it. The School alarm kept start 2026-10-19. Fix: new `Alarm.start_picked` flag (model.py), set only when the user picks a date in the editor. Otherwise the start date follows the time, including when the editor opens (ui/editor.py). Also fixed: the "Play each message N times" spin reused the name `self.repeat`, which is also the Repeat dropdown. Any time change that moved the start date, or picking a Repeat preset, threw an AttributeError. It is now `self.repeat_count`.
- [x] 14. ✅ The puzzle no longer opens a new fullscreen workspace. RingWindow is now a moderately sized, undecorated, non-resizable window (at least 600 px wide) on the current workspace. It is kept above other windows with _NET_WM_STATE_ABOVE (`keep_above` in ui/ringing.py, via libX11 ctypes, since GTK 4 has no API for this). The clock is now 64 px and "Good morning" 48 px (data/style.css). The sliding puzzle's goal thumbnail is pre-scaled to 150 px, because its native size was stretching the window. Verified under Gala on Xvfb: every puzzle reports _NET_WM_STATE_ABOVE, and the sizes range from 600x488 (math) to 780x813 (balloon).
- [x] 15. ✅ Messages are now a per-alarm playlist that can repeat the same recording. The checklist is replaced by numbered playlist rows, each with drag-to-reorder and a remove (x) button, plus an "[recording] Add to playlist" row. The playlist plays top to bottom with "Pause between messages" between entries, then loops. "Play each message N times" still applies to each entry. Existing alarms keep their checked messages, in order, as their playlist (Alarm.recordings already allowed duplicates). Files: ui/editor.py, plus a duplicate-entry test in tests/test_playlist.py. Verified on Xvfb: load, add, drag, remove, save and reopen, and app.playlist_files keeps the duplicates in order.
- [x] 16. ✅ Simon starts silently. The pattern no longer auto-plays: a "▶ Play pattern" button shows it, as many times as the player wants. While the pattern plays, the alarm messages are silenced (volume 0, was 25% for the whole puzzle), the pads ignore presses and the button is disabled. After that, the messages resume at full volume. A mistake or a new pattern no longer replays automatically; the feedback says to start again or press Play pattern. Watching again restarts entry from the first color. Files: puzzles/simon.py, audio.py (duck → 0.0), puzzles/base.py docstring, data/style.css (.simon-play). Verified on Xvfb with a fake player: volume 1.0 → 0.0 → 1.0, presses are ignored during playback, the mistake path and replay work, and solving rings off.
