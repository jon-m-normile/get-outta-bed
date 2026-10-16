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
