# Get Outta Bed! — Product Requirements (v1)

## 1. Summary

**Get Outta Bed!** is a desktop alarm clock for elementary OS. It wakes the user with a playlist of recorded voice messages that she chooses, and it keeps playing until she solves a short puzzle. There is no snooze. It runs on a family member's ~2016 iMac running elementary OS. That computer stays on overnight.

The user is a teenager who has been sleeping through alarms. Her parent records the wake-up messages, and she manages her own alarms. Success means the alarm reliably rings at the right time, loudly enough, and only stops once she's awake enough to solve a puzzle.

## 2. Platform and technical constraints

- **Target OS:** elementary OS 7.x or 8.x (Ubuntu 22.04 / 24.04 base). Check the version with `cat /etc/os-release` before you start, and support whichever one is installed.
- **Hardware:** a 2016 Intel iMac. Keep the app light. No Electron.
- **Language and toolkit:** Python 3 with PyGObject and **GTK4**, so the app looks native on elementary. Use Granite if it's easily available, but don't depend on it. Install dependencies from Ubuntu/elementary apt packages, not pip, wherever possible.
- **Audio playback:** GStreamer (`playbin`) through PyGObject. Install the plugins needed for MP3, M4A/AAC (iPhone Voice Memos), WAV, OGG and FLAC, including `gstreamer1.0-libav` for M4A.
- **System volume:** set through `pactl` (works with both PulseAudio and PipeWire's pulse layer). Unmute the default output, then set the alarm's volume.
- **Repeat rules:** store them as **iCalendar RRULE strings (RFC 5545)**, the same model Google Calendar uses, and calculate occurrences with `python-dateutil` (`dateutil.rrule`). Use the system's local time zone and handle daylight-saving changes correctly.
- **Data location:** `~/.local/share/get-outta-bed/`, holding `settings.json`, `recordings/` and `puzzle-photo.jpg`. Write JSON atomically (write to a temp file, then rename). If `settings.json` is corrupt, back it up and start fresh rather than crashing.
- **App ID:** `io.github.getouttabed.GetOuttaBed`. Run a single instance: launching the app again shows the existing window.

## 3. App presence

- **Icon and launcher:** install a `.desktop` file and an original scalable SVG icon (a cheerful alarm clock; no copyrighted characters) so "Get Outta Bed!" appears in the Applications menu and can be pinned to the dock with "Keep in Dock."
- **Always running:** closing the window hides it, and the process keeps running so alarms still fire. There's no tray icon, since elementary doesn't use them. Clicking the dock icon or launching the app again brings the window back. A **Quit** item in the app menu really does quit; we trust the user.
- **Autostart:** an autostart entry launches the app at login in background mode (`--background`, no window).
- **Sleep prevention:** while the app runs, stop the system from **suspending** automatically, via `Gtk.Application.inhibit` with the SUSPEND flag or logind's inhibit. The screen may still blank or lock.
- **Locked screen:** if the session is locked when an alarm fires, the audio still has to play. The puzzle window appears once she unlocks. Document this behavior.

## 4. Main window: alarm list

- A list of alarms sorted by time. Each row shows:
  - the time, large (12-hour format with AM/PM)
  - a repeat summary in plain English, e.g. "Weekdays", "Every 2 weeks on Mon, Thu", "Monthly on the third Friday", "Does not repeat — Sat, Oct 17"
  - the puzzle name (or "Surprise me")
  - an on/off switch
- Under the list: "Next alarm: Monday 6:45 AM."
- A **"+"** button adds an alarm. Clicking a row opens the editor. A delete button is in the editor, with a confirmation.
- Header-bar buttons: **Recordings** (library), **Puzzle photo**, and an app menu with About and Quit.
- When the list is empty, show a friendly prompt: "No alarms yet — add one with +".

## 5. Alarm editor

| Field | Behavior |
|---|---|
| **Time** | Hour, minute and AM/PM picker. Default is 7:00 AM. |
| **Label** | Optional text, e.g. "School." It's shown on the ringing screen. |
| **Repeat** | See 5.1. |
| **Maximum volume** | Slider from 10–100% (default **100%**): the level the volume ramp climbs to (see §8.1). It has a **▶ Test** button that plays the first selected recording at that volume for 5 seconds, then puts the volume back where it was. |
| **Messages** | See 5.2. |
| **Puzzle** | Dropdown with Picture Jigsaw, Sliding Tile, Balloon Pop, Math, Simon, or **Surprise me** (random each time, never the same puzzle twice in a row). |
| **Ring now (test)** | Fires this alarm immediately, with the full ringing screen and puzzle. |

Save and Cancel buttons. Turning an alarm on or off from the list doesn't open the editor.

### 5.1 Repeat (modeled on Google Calendar)

The dropdown presets are generated from the alarm's date, the next date it will ring:

| Preset | RRULE |
|---|---|
| Does not repeat | none (rings once, then switches itself off) |
| Daily | `FREQ=DAILY` |
| Weekly on {weekday} | `FREQ=WEEKLY;BYDAY=FR` |
| Monthly on the {nth weekday} | `FREQ=MONTHLY;BYDAY=3FR` (use `-1FR` for "last Friday" when it applies) |
| Annually on {Month Day} | `FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=16` |
| Every weekday (Monday to Friday) | `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR` |
| Custom… | opens the custom dialog |

**Custom dialog**, laid out like Google Calendar's:
- **Repeat every** [N] [day / week / month / year]
- **Weekly:** seven toggle buttons, S M T W T F S. At least one must be selected.
- **Monthly:** choose between "Monthly on day {16}" and "Monthly on the {third Friday}."
- **Ends:** ( ) Never · ( ) On [date picker] · ( ) After [N] occurrences
- A live summary line, e.g. "Every 2 weeks on Monday and Thursday, until Dec 19."

Also store a **start date** (DTSTART), which defaults to the next time the alarm time comes around. When a repeating alarm has no more occurrences, it switches itself off and shows "Ended."

### 5.2 Messages (playlist)

- Shows every recording in the library with a checkbox. Checked recordings play in the order shown, and she can drag them to reorder.
- A toggle switches between **Play in order** and **Shuffle**.
- The playlist loops with a 1.5-second gap between messages. In Shuffle mode, the same message never plays twice in a row.
- If no recordings are checked, or the files are missing, a built-in alarm tone plays instead. Use the freedesktop `alarm-clock-elapsed` sound, or bundle an original or public-domain tone.

## 6. Recordings library

- Add recordings with an **Add recordings…** file picker (multi-select) or by **dragging** files onto the library window.
- Files are **copied** into the app's data folder, so the originals can be moved or deleted afterwards.
- Accept MP3, M4A, AAC, WAV, OGG, OPUS and FLAC. Reject anything else with a clear message.
- Each row shows the name (defaulting to the file name without its extension), the duration, a **▶ Preview** button, **Rename**, and **Delete**. Delete asks for confirmation and removes the recording from every alarm's playlist.

## 7. Puzzle photo

- **Puzzle photo…** opens a dialog with the current photo, a **Choose photo…** button (JPG, PNG, HEIC if a decoder is available) and a **Reset to default** button.
- The photo is center-cropped to a square, downscaled to about 900 px, and saved as `puzzle-photo.jpg`.
- Until she picks a photo, use a bundled original default picture, colorful and with clear regions so it can be solved.

## 8. When an alarm rings

1. **Fire time:** check the schedule at least every 15 seconds. If the computer was asleep or busy and an occurrence was missed by **15 minutes or less**, ring now. If it was missed by more, skip it and log it. If two alarms come due together, ring once.
2. **Audio:** remember the current system volume, unmute the output, and start the playlist with the **volume ramp** (see §8.1).
3. **Ringing screen:** a fullscreen window brought to the front. It shows the time, the label, "Solve the puzzle to turn off the alarm," and the puzzle. There's no close button, Escape doesn't dismiss it, and closing the window just reopens it.
4. **Stopping:** the only way to stop the alarm is to solve the puzzle. When she does, the audio stops, she sees "Good morning! ☀️" for 2 seconds, and the window closes.
5. **Safety cap:** if the puzzle isn't solved within **60 minutes**, stop the audio, leave the screen up with "Alarm stopped after 60 minutes," and log it. Make this a single constant.
6. **Logging:** write each ring start (including the starting volume), the puzzle used, the time it was solved and how long it took, plus any errors, to `~/.local/share/get-outta-bed/log.txt`, keeping the last 1,000 lines.
7. **Afterwards:** once the alarm stops, set the system volume and mute state back to what they were before it rang.

### 8.1 Volume ramp

- The ramp **starts from the speakers' current system volume**, whatever it was when the alarm fired. If the output was muted, unmute it and start from the volume level it had while muted. If it was at 0%, start from 0%.
- The volume rises **linearly** from that starting level to the alarm's **maximum volume** over **180 seconds**. Update it at least once per second: `volume(t) = start + (max − start) × min(t, 180) / 180`.
- If the starting level is already at or above the maximum, play at the starting level for the whole ring. Never lower the volume.
- After 180 seconds, hold at the maximum. **Re-assert the volume and unmute every 10 seconds**, so if someone turns it down or mutes it, it goes straight back to the maximum.
- If the volume is turned down *during* the ramp, the ramp continues from the expected value at that moment and doesn't start over.
- `RAMP_SECONDS = 180` is a single constant. The ramp applies to the Ring now (test) button too.
- Volume is the system output level (0–100%, no boost beyond 100%). Set it with `pactl set-sink-volume @DEFAULT_SINK@ N%` or the GStreamer/PulseAudio equivalent. Leave the app's own playback volume at full.

## 9. Puzzles

Each puzzle should take a typical awake person about **15–30 seconds**. They need big, mouse-friendly targets, high contrast, and nothing that requires precise timing. The audio keeps playing the whole time. Every puzzle shows a small progress indicator.

**Fairness rule:** if she fails a puzzle three times (only possible in Math and Simon), give her a new instance of the same puzzle type. Never let it reach an unwinnable state.

1. **Picture Jigsaw:** the photo is cut into a 3×3 grid and scrambled into a random arrangement that isn't already solved, with at least 6 tiles out of place. She clicks one tile and then another to swap them, and dragging also works. A tile in its correct spot shows a subtle checkmark or border. The puzzle is solved when every tile is in place.
2. **Sliding Tile:** the photo is cut into a 3×3 grid with the bottom-right tile removed. Scramble it by making **15–25 random legal moves** from the solved state, so it's always solvable and short. Clicking a tile next to the gap slides it, and the arrow keys work too. Show a faint "goal" thumbnail. When it's solved, the missing tile fills in.
3. **Balloon Pop:** colorful balloons float upward at a gentle speed, a few at a time. She clicks them to pop them, with a pop animation and an original sound effect. Popping **10** solves it. Missed balloons simply float away and new ones keep coming, so there's no fail state.
4. **Math:** **3 problems** shown one at a time. Each is two-digit addition or subtraction (result 0–199) or a single-digit multiplication. Answers are typed into a large text field and checked on Enter. A wrong answer shakes the field and swaps in a new problem. After 3 wrong answers on the same set, generate a new set.
5. **Simon:** four large colored pads, each with its own tone, played over the quieted message audio or between messages. Show a sequence of **5** flashes, about 0.6 seconds apart, then she repeats it by clicking. A mistake replays the same sequence. After 3 failures, generate a new sequence.

**Surprise me** picks randomly among the five and never repeats the previous morning's puzzle.

## 10. Installation

- Ship a folder containing `install.sh`, `uninstall.sh` and `README.md`.
- `install.sh` must:
  - install the apt dependencies with `sudo apt install` (python3-gi, gir1.2-gtk-4.0, GStreamer plugins including libav, python3-dateutil, pulseaudio-utils or the equivalent)
  - copy the app to `~/.local/share/get-outta-bed/app/`
  - install the `.desktop` file to `~/.local/share/applications/`, the icon to `~/.local/share/icons/hicolor/scalable/apps/`, and the autostart entry to `~/.config/autostart/`
  - refresh the icon cache and start the app in the background
  - be safe to re-run for upgrades, keeping her alarms, recordings and photo
- `uninstall.sh` removes the app, launcher, icon and autostart entry, and asks before deleting her data.
- The README covers install, pinning to the dock, adding recordings, the locked-screen behavior, and troubleshooting: checking the log and testing the sound.

## 11. Testing and acceptance

**Automated tests (pytest)**
- Recurrence: every preset, every Custom combination (interval, weekdays, monthly by day and by Nth weekday, last-weekday, ending on a date or after N times), DST transitions in America/New_York (the spring-forward gap and the fall-back repeated hour), and Feb 29 / 31st-of-the-month cases.
- Scheduler: missed-alarm catch-up within 15 minutes and skip beyond it, duplicate suppression, and one-time alarms switching themselves off.
- Volume ramp, with time faked: the start level is used at t=0, the volume is at the halfway point at t=90 s and at the maximum at t≥180 s, it's never lowered when the start is above the maximum, and a muted start gets unmuted.
- Puzzle logic, separate from the UI: jigsaw scrambles are never already solved, sliding scrambles are always solvable, the math answer checker works, and the Simon sequence comparison works.
- Settings: the save/load round trip and recovery from a corrupt file.

**Manual acceptance checklist (on the iMac)**
- [ ] The app appears in the Applications menu with its icon and can be kept in the dock.
- [ ] Closing the window keeps alarms working, and the app comes back after logout/login and after a reboot.
- [ ] An alarm set 2 minutes ahead rings on time even after the system was muted and turned down. It starts at the previous volume, reaches the maximum volume after 3 minutes, and returns to the previous volume once the puzzle is solved.
- [ ] Turning the volume down while the alarm is ringing gets corrected within 10 seconds (after the ramp) or within 1 second (during the ramp).
- [ ] Recordings play in the chosen order and in Shuffle mode, and loop.
- [ ] Each of the five puzzles stops the alarm, and nothing else does (the close button, Escape, Alt+F4).
- [ ] Weekly, monthly-Nth-weekday and Custom repeats show correct "Next alarm" times.
- [ ] Recordings from iPhone Voice Memos (.m4a) import and play.
- [ ] An uploaded photo appears in the Jigsaw and Sliding Tile puzzles.
- [ ] The computer doesn't suspend overnight while the app is running.

## 12. Out of scope for v1

Snooze; backup phone calls or push alerts (possibly a later "wake a parent" feature); parental PIN; remote control from a phone; recording audio inside the app; multiple user profiles.

## 13. Build guidance for the developer (Claude Code)

- Build and test **on the target iMac** if possible, so the sound, dock, autostart and fullscreen behavior can be checked for real.
- Ask before running `sudo` commands or changing system settings.
- Suggested order:
  1. data model and recurrence, with tests
  2. scheduler and audio engine
  3. main window and editor
  4. recordings library and photo
  5. ringing screen
  6. the five puzzles, one at a time, each testable via **Ring now (test)**
  7. installer, icon and README
  8. a pass through the acceptance checklist
- Keep the code modular: `model.py`, `recurrence.py`, `scheduler.py`, `audio.py`, `ui/` and `puzzles/`, with one file per puzzle behind a common interface (`start()`, a `solved` signal, `reset()`).
- All art and sounds must be original or public domain.
